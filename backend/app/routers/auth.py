import datetime as dt
import hmac
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.csrf import csrf_cookie_kwargs, expose_csrf_token, mirror_csrf_cookie_header, new_csrf_token
from app.core.database import get_db
from app.core.deps import create_session_value, get_current_user, require_user
from app.core.email import otp_email, password_reset_email, send_email, welcome_email
from app.core.notify import notify
from app.core.permissions import ROLE_DEALER, ROLE_DISTRIBUTOR, ROLE_FARMER, ROLE_SUPER_ADMIN, STAFF_ROLES
from app.core.rate_limit import rate_limiter
from app.core.security import (
    generate_token,
    hash_password,
    hash_token,
    password_strength_errors,
    verify_password,
    verify_password_or_dummy,
)
from app.models.models import FarmerProfile, OtpCode, PasswordResetToken, User
from app.schemas.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterFarmerRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserOut,
    VerifyOtpRequest,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()

GENERIC_LOGIN_ERROR = "Incorrect email or password."

# Roles whose sign-ins the owner (super_admin) is notified about - staff and
# super_admin's own logins are not, since those are the owner's own team,
# not the outside parties this notification is for.
NOTIFY_OWNER_ON_LOGIN_ROLES = {ROLE_FARMER, ROLE_DEALER, ROLE_DISTRIBUTOR}

# Roles that must confirm a second factor (an emailed code) before a
# password-correct login actually issues a session. Farmers are excluded -
# a farmer account already goes through an OTP at signup and carries lower
# stakes than a login that can manage the business (staff) or a commercial
# partner account (dealer/distributor).
OTP_LOGIN_ROLES = STAFF_ROLES | {ROLE_DEALER, ROLE_DISTRIBUTOR}


def _rotate_session_version(db: Session, user: User) -> None:
    """Generates a fresh session marker and persists it before the next
    session cookie is issued - enforces a single active session per
    account (see deps.get_current_user): any token issued before this
    commit, including one still active in another browser or device,
    stops authenticating the instant this lands, with no server-side
    session store required since the marker travels inside the signed
    token itself."""
    user.session_version = uuid.uuid4().hex
    db.commit()


def _notify_owner_of_login(db: Session, user: User) -> None:
    if user.role not in NOTIFY_OWNER_ON_LOGIN_ROLES:
        return
    owners = db.query(User).filter(User.role == ROLE_SUPER_ADMIN).all()
    for owner in owners:
        notify(
            db, recipient_id=owner.id, type="user_login",
            title=f"{user.role.replace('_', ' ').title()} signed in",
            message=f"{user.full_name} ({user.email}) signed in.",
            related_entity_type="user", related_entity_id=user.id,
        )
    if owners:
        db.commit()


def _issue_session(response: Response, user: User) -> None:
    """Sets both the HttpOnly session cookie and the readable CSRF cookie.
    Called on every event that establishes or rotates a session (register,
    login, password change, password reset) so a stale CSRF token from
    before never lingers."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=create_session_value(user),
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    token = new_csrf_token()
    response.set_cookie(value=token, **csrf_cookie_kwargs())
    expose_csrf_token(response, token)


@router.post("/register", response_model=UserOut)
def register_farmer(payload: RegisterFarmerRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    limiter_key = f"register:{request.client.host if request.client else 'unknown'}"
    if not rate_limiter.check(limiter_key, settings.PUBLIC_FORM_RATE_LIMIT_ATTEMPTS, settings.PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    errors = password_strength_errors(payload.password)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=ROLE_FARMER,
        full_name=payload.full_name,
        phone=payload.phone,
        status="active",
        password_changed_at=dt.datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    db.add(FarmerProfile(user_id=user.id))
    record_audit(db, actor_id=user.id, action="user.register", entity_type="user", entity_id=user.id,
                 summary=f"Farmer account registered: {user.email}")
    db.commit()
    db.refresh(user)
    _rotate_session_version(db, user)
    _issue_session(response, user)

    html, text = welcome_email(user.full_name, "Farmer")
    send_email(to=user.email, subject="Welcome to Rockstar Organics", html=html, text=text)
    return user


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


@router.post("/signup")
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    """OTP-gated signup, per the real-world content spec: signup ->
    validation -> OTP verification -> account creation -> login. No User
    row is created until the OTP is verified (see verify_otp below) - the
    pending account data is held in OtpCode until then."""
    limiter_key = f"signup:{request.client.host if request.client else 'unknown'}"
    if not rate_limiter.check(limiter_key, settings.PUBLIC_FORM_RATE_LIMIT_ATTEMPTS, settings.PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many signup attempts. Please try again later.")

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    errors = password_strength_errors(payload.password)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    # Replace any prior unconsumed OTP for this email so only the latest
    # signup attempt's code is valid.
    db.query(OtpCode).filter(OtpCode.email == payload.email.lower(), OtpCode.purpose == "signup", OtpCode.consumed_at.is_(None)).delete()

    code = _generate_otp_code()
    otp = OtpCode(
        email=payload.email.lower(),
        code_hash=hash_token(code, settings.SECRET_KEY),
        purpose="signup",
        pending_full_name=payload.full_name,
        pending_phone=payload.phone,
        pending_password_hash=hash_password(payload.password),
        pending_role=ROLE_FARMER,
        expires_at=dt.datetime.utcnow() + dt.timedelta(minutes=settings.OTP_TTL_MINUTES),
    )
    db.add(otp)
    record_audit(db, actor_id=None, action="user.signup_otp_requested", entity_type="user", entity_id=None,
                 summary=f"Signup OTP requested for {payload.email.lower()}")
    db.commit()

    html, text = otp_email(code)
    email_result = send_email(to=payload.email, subject="Your Rockstar Organics verification code", html=html, text=text)

    response = {"ok": True, "message": "A verification code has been sent to your email.", "email_sent": email_result.sent}
    # DEV_EXPOSE_OTP is its own explicit gate, independent of ENVIRONMENT -
    # see Settings.DEV_EXPOSE_OTP's docstring. Unlike some providers, Brevo
    # has no sandbox restriction once EMAIL_FROM_EMAIL is a verified sender,
    # so DEV_EXPOSE_OTP should be turned off in production as soon as that
    # verification is confirmed working end-to-end.
    if settings.DEV_EXPOSE_OTP:
        response["dev_otp_code"] = code
    return response


@router.post("/verify-otp", response_model=UserOut)
def verify_otp(payload: VerifyOtpRequest, response: Response, db: Session = Depends(get_db)):
    otp = (
        db.query(OtpCode)
        .filter(OtpCode.email == payload.email.lower(), OtpCode.purpose == "signup", OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.created_at.desc())
        .first()
    )
    if not otp or otp.expires_at < dt.datetime.utcnow():
        raise HTTPException(status_code=400, detail="This verification code is invalid or has expired. Please sign up again.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Too many incorrect attempts. Please sign up again to get a new code.")

    if not hmac.compare_digest(hash_token(payload.code, settings.SECRET_KEY), otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    existing = db.query(User).filter(User.email == otp.email).first()
    if existing:
        otp.consumed_at = dt.datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = User(
        email=otp.email,
        password_hash=otp.pending_password_hash,
        role=otp.pending_role,
        full_name=otp.pending_full_name,
        phone=otp.pending_phone,
        status="active",
        email_verified=True,
        password_changed_at=dt.datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    if user.role == ROLE_FARMER:
        db.add(FarmerProfile(user_id=user.id))
    otp.consumed_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="user.signup_verified", entity_type="user", entity_id=user.id,
                 summary=f"Account created via OTP-verified signup: {user.email}")
    db.commit()
    db.refresh(user)
    _rotate_session_version(db, user)
    _issue_session(response, user)

    html, text = welcome_email(user.full_name, "Farmer")
    send_email(to=user.email, subject="Welcome to Rockstar Organics", html=html, text=text)
    return user


def _finish_login(db: Session, request: Request, response: Response, user: User) -> UserOut:
    """The actual "you are now signed in" step: audit log, owner
    notification, session-version rotation, and issuing the session/CSRF
    cookies. Called directly from login() for roles that skip OTP, and from
    verify_login_otp() once the second factor has been confirmed - either
    way, this is the single place a session actually gets issued."""
    record_audit(db, actor_id=user.id, action="user.login", entity_type="user", entity_id=user.id,
                 summary=f"User signed in: {user.email}",
                 ip_address=request.client.host if request.client else None,
                 user_agent=request.headers.get("user-agent"))
    db.commit()
    _notify_owner_of_login(db, user)
    _rotate_session_version(db, user)
    _issue_session(response, user)
    return UserOut.model_validate(user)


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    limiter_key = f"login:{request.client.host if request.client else 'unknown'}:{payload.email.lower()}"
    if not rate_limiter.check(limiter_key, settings.LOGIN_RATE_LIMIT_ATTEMPTS, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

    user = db.query(User).filter(User.email == payload.email.lower()).first()
    password_ok = verify_password_or_dummy(payload.password, user.password_hash if user else None)
    if not user or not password_ok:
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)
    if user.status != "active":
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    if user.role in OTP_LOGIN_ROLES:
        # Password confirmed, but no session yet - a code is emailed and
        # must be confirmed at /login/verify-otp before _finish_login runs.
        # Replaces any prior unconsumed login OTP for this email, same as
        # signup, so only the latest requested code is valid.
        db.query(OtpCode).filter(OtpCode.email == user.email, OtpCode.purpose == "login", OtpCode.consumed_at.is_(None)).delete()
        code = _generate_otp_code()
        db.add(OtpCode(
            email=user.email,
            code_hash=hash_token(code, settings.SECRET_KEY),
            purpose="login",
            expires_at=dt.datetime.utcnow() + dt.timedelta(minutes=settings.OTP_TTL_MINUTES),
        ))
        record_audit(db, actor_id=user.id, action="user.login_otp_requested", entity_type="user", entity_id=user.id,
                     summary=f"Login verification code requested for {user.email}")
        db.commit()

        html, text = otp_email(code)
        email_result = send_email(to=user.email, subject="Your Rockstar Organics sign-in code", html=html, text=text)
        otp_response = {
            "otp_required": True,
            "email": user.email,
            "message": "Enter the verification code we emailed you to finish signing in.",
            "email_sent": email_result.sent,
        }
        # Same DEV_EXPOSE_OTP gate as signup - see its docstring in config.py.
        if settings.DEV_EXPOSE_OTP:
            otp_response["dev_otp_code"] = code
        return otp_response

    return _finish_login(db, request, response, user)


@router.post("/login/verify-otp")
def verify_login_otp(payload: VerifyOtpRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    limiter_key = f"login-otp:{request.client.host if request.client else 'unknown'}:{payload.email.lower()}"
    if not rate_limiter.check(limiter_key, settings.LOGIN_RATE_LIMIT_ATTEMPTS, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")

    otp = (
        db.query(OtpCode)
        .filter(OtpCode.email == payload.email.lower(), OtpCode.purpose == "login", OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.created_at.desc())
        .first()
    )
    if not otp or otp.expires_at < dt.datetime.utcnow():
        raise HTTPException(status_code=400, detail="This verification code is invalid or has expired. Please sign in again.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Too many incorrect attempts. Please sign in again to get a new code.")

    if not hmac.compare_digest(hash_token(payload.code, settings.SECRET_KEY), otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    user = db.query(User).filter(User.email == otp.email).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=400, detail="This verification code is invalid or has expired. Please sign in again.")

    otp.consumed_at = dt.datetime.utcnow()
    db.commit()
    return _finish_login(db, request, response, user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie("rso_csrf", path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut | None)
def me(request: Request, response: Response, user: User | None = Depends(get_current_user)):
    if user is not None:
        mirror_csrf_cookie_header(request, response)
    return user


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, response: Response, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Lets a signed-in user (including one with must_change_password set,
    e.g. a freshly approved dealer or invited staff member) change their
    own password by proving they know the current one. This is distinct
    from the forgot-password flow, which is for someone who is locked out."""
    # Rate limited per user (not per IP): this endpoint requires an
    # authenticated session, so the realistic threat isn't an anonymous
    # brute force, it's a hijacked/stolen session being used to grind
    # through current_password guesses - and each guess costs a real
    # Argon2 verification, so unlimited attempts is also a cheap CPU-DoS
    # lever against the server itself.
    limiter_key = f"change-password:{user.id}"
    if not rate_limiter.check(limiter_key, settings.LOGIN_RATE_LIMIT_ATTEMPTS, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    errors = password_strength_errors(payload.new_password)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="New password must be different from the current password.")

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.password_changed_at = dt.datetime.utcnow()
    record_audit(db, actor_id=user.id, action="user.password_changed", entity_type="user", entity_id=user.id,
                 summary="Password changed by user")
    db.commit()
    db.refresh(user)
    _rotate_session_version(db, user)
    _issue_session(response, user)  # old sessions/tokens are now invalid; reissue this one
    return user


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    limiter_key = f"forgot:{request.client.host if request.client else 'unknown'}"
    if not rate_limiter.check(limiter_key, settings.PUBLIC_FORM_RATE_LIMIT_ATTEMPTS, settings.PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    user = db.query(User).filter(User.email == payload.email.lower()).first()
    # `email_sent` is included in every response path, not just this one -
    # if only the "user exists" branch added the key, its mere presence in
    # the JSON (independent of its value) would let an attacker enumerate
    # registered emails by checking for the key rather than reading the
    # (deliberately identical) message text.
    generic_response = {"ok": True, "message": "If that email exists, a reset link has been generated.", "email_sent": False}
    if not user:
        return generic_response

    token = generate_token()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(token, settings.SECRET_KEY),
        expires_at=dt.datetime.utcnow() + dt.timedelta(minutes=settings.PASSWORD_RESET_TOKEN_TTL_MINUTES),
    )
    db.add(reset)
    record_audit(db, actor_id=user.id, action="user.password_reset_requested", entity_type="user", entity_id=user.id,
                 summary="Password reset requested")
    db.commit()

    reset_url = f"{settings.PUBLIC_APP_URL}/reset-password?token={token}"
    html, text = password_reset_email(reset_url)
    email_result = send_email(to=user.email, subject="Reset your Rockstar Organics password", html=html, text=text)
    generic_response["email_sent"] = email_result.sent

    # See the matching comment in signup() above: DEV_EXPOSE_RESET_TOKEN is
    # its own explicit gate now, independent of ENVIRONMENT.
    if settings.DEV_EXPOSE_RESET_TOKEN:
        generic_response["dev_reset_token"] = token
    return generic_response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    # The token itself is 256 bits of entropy (secrets.token_urlsafe(32)),
    # so this limiter is defense-in-depth against generic endpoint abuse
    # rather than a meaningful brute-force barrier on its own.
    limiter_key = f"reset-password:{request.client.host if request.client else 'unknown'}"
    if not rate_limiter.check(limiter_key, settings.PUBLIC_FORM_RATE_LIMIT_ATTEMPTS, settings.PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")

    errors = password_strength_errors(payload.new_password)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    token_hash = hash_token(payload.token, settings.SECRET_KEY)
    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    if not reset or reset.used_at or reset.expires_at < dt.datetime.utcnow():
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user = db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.password_changed_at = dt.datetime.utcnow()
    now = dt.datetime.utcnow()
    reset.used_at = now
    # Invalidate every other outstanding reset token for this user too (e.g.
    # from an earlier forgot-password request) - otherwise a stale, still-
    # unexpired token can reset the password again after this one already
    # completed.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != reset.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now})
    record_audit(db, actor_id=user.id, action="user.password_reset_completed", entity_type="user", entity_id=user.id,
                 summary="Password reset completed")
    db.commit()
    return {"ok": True}
