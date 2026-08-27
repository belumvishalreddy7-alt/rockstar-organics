"""
Environment doctor: checks common local-development problems before you
try to start the server, per spec section 39 (Windows developer experience).

Run with: python -m scripts.doctor
"""
import importlib.util
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHECKS_FAILED = []


def check(label, ok, hint=""):
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {label}")
    if not ok:
        CHECKS_FAILED.append(label)
        if hint:
            print(f"        -> {hint}")


def main():
    check("Python 3.11+", sys.version_info >= (3, 11), "Install Python 3.11 or newer.")

    for pkg in ["fastapi", "sqlalchemy", "alembic", "pydantic", "argon2", "itsdangerous", "multipart"]:
        check(f"Dependency installed: {pkg}", importlib.util.find_spec(pkg) is not None,
              "Run: pip install -r requirements.txt")

    check(".env file present", Path(".env").exists(),
          "Copy .env.example to .env and adjust values.")

    port_free = True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        port_free = s.connect_ex(("127.0.0.1", 8000)) != 0
    check("Port 8000 available", port_free, "Stop the process using port 8000, or run uvicorn on a different port.")

    upload_root = Path(os.environ.get("UPLOAD_ROOT", "./uploads"))
    upload_root.mkdir(parents=True, exist_ok=True)
    check("Upload folder writable", os.access(upload_root, os.W_OK))

    if CHECKS_FAILED:
        print(f"\n{len(CHECKS_FAILED)} check(s) failed. Fix the items above before starting the server.")
        sys.exit(1)
    print("\nAll checks passed. You can start the server.")


if __name__ == "__main__":
    main()
