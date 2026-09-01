import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { api, ApiError } from "../../api/client";
import { PasswordInput } from "../../components/PasswordInput";

function goToRoleHome(navigate: ReturnType<typeof useNavigate>, role: string) {
  if (role === "farmer") navigate("/farmer");
  else if (role === "dealer") navigate("/dealer");
  else if (role === "distributor") navigate("/distributor");
  else navigate("/staff");
}

export function Login() {
  const { login, verifyLoginOtp } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<"credentials" | "otp">("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [emailSent, setEmailSent] = useState<boolean | null>(null);
  const [devOtp, setDevOtp] = useState<string | null>(null);

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Sign in</h1>
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {step === "credentials" && (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setPending(true);
              setError(null);
              try {
                const result = await login(email, password);
                if ("otp_required" in result) {
                  setEmailSent(result.email_sent);
                  setDevOtp(result.dev_otp_code || null);
                  setStep("otp");
                } else {
                  goToRoleHome(navigate, result.role);
                }
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Unable to sign in.");
              } finally {
                setPending(false);
              }
            }}
          >
            <div className="field"><label htmlFor="email">Email</label>
              <input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
            <div className="field"><label htmlFor="password">Password</label>
              <PasswordInput id="password" required autoComplete="current-password" value={password} onChange={setPassword} /></div>
            <button className="btn btn-primary" type="submit" disabled={pending}>{pending ? "Signing in..." : "Sign in"}</button>
          </form>
        )}
        {step === "otp" && (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setPending(true);
              setError(null);
              try {
                const user = await verifyLoginOtp(email, code);
                goToRoleHome(navigate, user.role);
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Incorrect or expired verification code.");
              } finally {
                setPending(false);
              }
            }}
          >
            <p className="small muted">
              {emailSent
                ? <>We emailed a 6-digit verification code to <strong>{email}</strong>.</>
                : "Email delivery is not configured in this environment, so the code below is shown directly (this only happens in development)."}
            </p>
            {devOtp && (
              <div className="alert alert-info">Development mode: your code is <strong>{devOtp}</strong>.</div>
            )}
            <div className="field"><label htmlFor="login-otp-code">Verification code</label>
              <input type="text" id="login-otp-code" required inputMode="numeric" maxLength={6} autoFocus value={code} onChange={(e) => setCode(e.target.value)} /></div>
            <button className="btn btn-primary" type="submit" disabled={pending}>{pending ? "Verifying..." : "Verify and sign in"}</button>
            <button type="button" className="btn btn-ghost" style={{ marginLeft: 8 }} onClick={() => { setStep("credentials"); setCode(""); setError(null); }}>
              Back
            </button>
          </form>
        )}
        <p className="small" style={{ marginTop: 12 }}>
          <Link to="/forgot-password">Forgot your password?</Link> · <Link to="/signup">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

export function Register() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Create a farmer account</h1>
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setPending(true);
            setError(null);
            try {
              await api.post("/auth/register", form);
              await refresh();
              navigate("/farmer");
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Unable to register.");
            } finally {
              setPending(false);
            }
          }}
        >
          <div className="field"><label htmlFor="full_name">Full name</label>
            <input type="text" id="full_name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
          <div className="field"><label htmlFor="email">Email</label>
            <input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          <div className="field"><label htmlFor="phone">Phone (10-digit mobile)</label>
            <input type="text" id="phone" required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
          <div className="field"><label htmlFor="password">Password</label>
            <PasswordInput id="password" required autoComplete="new-password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} />
            <p className="hint">At least 10 characters, with a letter and a digit.</p></div>
          <button className="btn btn-primary" type="submit" disabled={pending}>{pending ? "Creating account..." : "Create account"}</button>
        </form>
      </div>
    </div>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [devToken, setDevToken] = useState<string | null>(null);
  const [emailUncertain, setEmailUncertain] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Reset your password</h1>
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {message && <div className="alert alert-info">{message}</div>}
        {/* email_sent is false both when there's no account for that address
            and when there IS an account but delivery failed/isn't configured -
            those two cases are deliberately indistinguishable from the
            outside (see backend/app/routers/auth.py forgot_password), so
            this note never confirms or denies the account exists; it just
            tells a real user honestly that they may not receive anything. */}
        {emailUncertain && !devToken && (
          <div className="alert alert-info">
            If an account exists for that address, we could not confirm email delivery just now. If nothing arrives in a few minutes, please contact support.
          </div>
        )}
        {devToken && (
          <div className="alert alert-info">
            Development mode: <Link to={`/reset-password?token=${devToken}`}>use this reset link</Link> (would be emailed in production).
          </div>
        )}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setPending(true);
            setError(null);
            try {
              const r = await api.post<{ ok: boolean; message: string; email_sent: boolean; dev_reset_token?: string }>("/auth/forgot-password", { email });
              setMessage(r.message);
              setDevToken(r.dev_reset_token || null);
              setEmailUncertain(!r.email_sent);
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
            } finally {
              setPending(false);
            }
          }}
        >
          <div className="field"><label htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <button className="btn btn-primary" type="submit" disabled={pending}>{pending ? "Sending..." : "Send reset link"}</button>
        </form>
      </div>
    </div>
  );
}

export function ResetPassword() {
  const params = new URLSearchParams(window.location.search);
  const [token, setToken] = useState(params.get("token") || "");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Set a new password</h1>
      <div className="panel">
        {done ? (
          <div className="alert alert-success">Password updated. <Link to="/login">Sign in</Link>.</div>
        ) : (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api.post("/auth/reset-password", { token, new_password: password });
                setDone(true);
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Unable to reset password.");
              }
            }}
          >
            {error && <div className="alert alert-error">{error}</div>}
            <div className="field"><label htmlFor="token">Reset token</label>
              <input type="text" id="token" required value={token} onChange={(e) => setToken(e.target.value)} /></div>
            <div className="field"><label htmlFor="new_password">New password</label>
              <PasswordInput id="new_password" required autoComplete="new-password" value={password} onChange={setPassword} /></div>
            <button className="btn btn-primary" type="submit">Set new password</button>
          </form>
        )}
      </div>
    </div>
  );
}
