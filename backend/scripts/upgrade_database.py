"""
Apply pending Alembic migrations. Wraps `alembic upgrade head` with a
pre-flight message; does not delete or overwrite any existing data.

Usage: python -m scripts.upgrade_database
"""
import subprocess
import sys


def run():
    print("Applying database migrations (alembic upgrade head)...")
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"])
    if result.returncode != 0:
        print("Migration failed. No destructive action was taken automatically; review the error above.")
        sys.exit(result.returncode)
    print("Migrations applied successfully.")


if __name__ == "__main__":
    run()
