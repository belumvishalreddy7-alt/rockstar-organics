"""
Bootstrap the first Super Administrator account.

This is the documented, secure bootstrap process referenced in spec section
7: staff accounts are never publicly self-registered, so the very first
account must be created directly against the database via this script.

Interactive usage (local development):
    python -m scripts.create_superadmin --email admin@example.com --name "Admin Name"

You will be prompted for a password (not passed on the command line, so it
does not end up in shell history). The password must meet the platform's
strength requirements.

Non-interactive usage (scripted production bootstrap, e.g. a platform's
one-off/release shell where there is no TTY for getpass): set
SUPERADMIN_EMAIL, SUPERADMIN_NAME and SUPERADMIN_PASSWORD as environment
variables and run with no arguments:
    python -m scripts.create_superadmin
This path is intentionally still explicit opt-in (three env vars must all
be set) and still idempotent - it silently does nothing if that email
already exists, so it is safe to run on every deploy/restart.
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.core.permissions import ROLE_SUPER_ADMIN
from app.core.security import hash_password, password_strength_errors
from app.models.models import User


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=os.environ.get("SUPERADMIN_EMAIL"))
    parser.add_argument("--name", default=os.environ.get("SUPERADMIN_NAME"))
    args = parser.parse_args()

    if not args.email or not args.name:
        print("Nothing to do: no --email/--name given and SUPERADMIN_EMAIL/SUPERADMIN_NAME are not set.")
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email.lower()).first()
        if existing:
            print(f"A user with email {args.email} already exists (role={existing.role}). Nothing to do.")
            return

        env_password = os.environ.get("SUPERADMIN_PASSWORD")
        if env_password:
            password = confirm = env_password
        else:
            password = getpass.getpass("Set Super Administrator password: ")
            confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match. Aborting.")
            return
        errors = password_strength_errors(password)
        if errors:
            print("Password does not meet requirements:")
            for e in errors:
                print(f"  - {e}")
            return

        user = User(email=args.email.lower(), password_hash=hash_password(password), role=ROLE_SUPER_ADMIN,
                    full_name=args.name, status="active", must_change_password=False, email_verified=True)
        db.add(user)
        db.commit()
        print(f"Super Administrator account created: {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
