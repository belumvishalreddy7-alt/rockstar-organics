"""
Builds backend/vercel_dist/: a functionally-identical copy of the app,
consolidated into far fewer files, for deployment through a tool that must
receive the entire file tree as literal content in one call (so file COUNT,
not just total size, is a real constraint). The original backend/app tree is
never modified - this script only reads it and writes into vercel_dist/.

Consolidation:
  - app/core/*.py (12 files)              -> app/core_bundle.py
  - app/routers/*.py (20) + services/matching.py -> app/routers_bundle.py
  - app/models/models.py                  -> copied, with its Base import
                                             repointed at app.core_bundle
  - app/models/__init__.py, app/schemas/schemas.py, app/main.py, api/index.py,
    requirements.txt, vercel.json         -> copied (main.py's imports
                                             repointed at the bundles)

Verified after building by scripts/smoke_test_vercel_dist.py (separate step).
"""
import re
from pathlib import Path

SRC = Path(__file__).parent
DIST = SRC / "vercel_dist"

CORE_ORDER = [
    "config", "security", "database", "audit", "permissions",
    "references", "rate_limit", "csrf", "email", "notify", "uploads", "deps",
]

ROUTER_FILES = [
    "accounts", "agriculture_photos", "announcements", "auth", "cases",
    "categories", "company_documents", "dealers", "distributors", "enquiries",
    "knowledge", "media", "notifications", "products", "reports", "reviews",
    "settings_router", "staff", "tasks", "visits",
]
# settings_router.py's router var is renamed to avoid a confusing
# "settings_router_router" name.
ROUTER_VAR_NAME = {name: ("company_settings_router" if name == "settings_router" else f"{name}_router") for name in ROUTER_FILES}

INTRA_CORE_IMPORT_RE = re.compile(r"^from app\.core\.\w+ import .+\n", re.MULTILINE)
CROSS_CORE_IMPORT_RE = re.compile(r"^from app\.core\.\w+ import (.+)$", re.MULTILINE)
INTRA_SERVICES_IMPORT_RE = re.compile(r"^from app\.services\.matching import .+\n", re.MULTILINE)


def build_core_bundle():
    parts = ['"""Consolidated app/core/*.py - see build_vercel_dist.py."""\n']
    for name in CORE_ORDER:
        text = (SRC / "app" / "core" / f"{name}.py").read_text()
        # Drop the module's own docstring-only leading triple-quoted block is
        # kept (harmless, just documentation) - only strip intra-app.core
        # imports, since those names are now in this same module.
        text = INTRA_CORE_IMPORT_RE.sub("", text)
        parts.append(f"\n# ===== app/core/{name}.py =====\n")
        parts.append(text)
    DIST_core = DIST / "app" / "core_bundle.py"
    DIST_core.write_text("".join(parts))
    print(f"wrote {DIST_core} ({DIST_core.stat().st_size} bytes)")


def build_routers_bundle():
    parts = ['"""Consolidated app/routers/*.py + app/services/matching.py - see build_vercel_dist.py."""\n']
    matching_text = (SRC / "app" / "services" / "matching.py").read_text()
    # matching.py has no app.core/app.routers deps, only sqlalchemy + models.
    parts.append("\n# ===== app/services/matching.py =====\n")
    parts.append(matching_text)

    for name in ROUTER_FILES:
        text = (SRC / "app" / "routers" / f"{name}.py").read_text()
        text = CROSS_CORE_IMPORT_RE.sub(r"from app.core_bundle import \1", text)
        text = INTRA_SERVICES_IMPORT_RE.sub("", text)  # matching already in this file
        var = ROUTER_VAR_NAME[name]
        # Rename this file's `router` object to its unique name. Do the
        # assignment first, then the decorator usages, so we don't
        # accidentally rewrite the thing we just wrote.
        text = re.sub(r"^router = APIRouter\(", f"{var} = APIRouter(", text, flags=re.MULTILINE)
        text = re.sub(r"@router\.", f"@{var}.", text)
        parts.append(f"\n# ===== app/routers/{name}.py =====\n")
        parts.append(text)

    DIST_routers = DIST / "app" / "routers_bundle.py"
    DIST_routers.write_text("".join(parts))
    print(f"wrote {DIST_routers} ({DIST_routers.stat().st_size} bytes)")


def build_models():
    text = (SRC / "app" / "models" / "models.py").read_text()
    text = text.replace(
        "from app.core.database import Base",
        "from app.core_bundle import Base",
    )
    (DIST / "app" / "models" / "models.py").write_text(text)
    (DIST / "app" / "models" / "__init__.py").write_text((SRC / "app" / "models" / "__init__.py").read_text())


def build_main():
    text = (SRC / "app" / "main.py").read_text()

    text = text.replace(
        "from app.core.config import get_settings\n"
        "from app.core.csrf import enforce_csrf\n"
        "from app.core.database import SessionLocal, engine\n"
        "from app.routers import (\n"
        "    accounts,\n"
        "    agriculture_photos,\n"
        "    announcements,\n"
        "    auth,\n"
        "    categories,\n"
        "    company_documents,\n"
        "    dealers,\n"
        "    distributors,\n"
        "    enquiries,\n"
        "    cases,\n"
        "    knowledge,\n"
        "    media,\n"
        "    notifications,\n"
        "    products,\n"
        "    reports,\n"
        "    reviews,\n"
        "    settings_router,\n"
        "    staff,\n"
        "    tasks,\n"
        "    visits,\n"
        ")\n",
        "from app.core_bundle import get_settings, enforce_csrf, SessionLocal, engine\n"
        "from app.routers_bundle import (\n"
        "    accounts_router,\n"
        "    agriculture_photos_router,\n"
        "    announcements_router,\n"
        "    auth_router,\n"
        "    categories_router,\n"
        "    company_documents_router,\n"
        "    dealers_router,\n"
        "    distributors_router,\n"
        "    enquiries_router,\n"
        "    cases_router,\n"
        "    knowledge_router,\n"
        "    media_router,\n"
        "    notifications_router,\n"
        "    products_router,\n"
        "    reports_router,\n"
        "    reviews_router,\n"
        "    company_settings_router,\n"
        "    staff_router,\n"
        "    tasks_router,\n"
        "    visits_router,\n"
        ")\n",
    )

    text = text.replace(
        "        from app.core.database import Base, SessionLocal, engine\n"
        "        from app.core.permissions import ROLE_SUPER_ADMIN\n"
        "        from app.core.security import hash_password, password_strength_errors\n"
        "        from app.models.models import CompanySetting, User\n"
        "        from app.routers.settings_router import REQUIRED_KEYS\n",
        "        from app.core_bundle import Base, SessionLocal, engine, ROLE_SUPER_ADMIN, hash_password, password_strength_errors\n"
        "        from app.models.models import CompanySetting, User\n"
        "        from app.routers_bundle import REQUIRED_KEYS\n",
    )

    for name in ROUTER_FILES:
        var = ROUTER_VAR_NAME[name]
        old_module = "settings_router" if name == "settings_router" else name
        text = text.replace(f"app.include_router({old_module}.router)", f"app.include_router({var})")

    text = text.replace(
        "from app.core.rate_limit import rate_limiter, RedisRateLimiter",
        "from app.core_bundle import rate_limiter, RedisRateLimiter",
    )

    remaining = CROSS_CORE_IMPORT_RE.findall(text)
    if remaining:
        raise SystemExit(f"main.py still has unrewritten app.core.* imports: {remaining}")

    (DIST / "app" / "main.py").write_text(text)


def copy_static():
    (DIST / "app" / "schemas").mkdir(parents=True, exist_ok=True)
    (DIST / "app" / "schemas" / "schemas.py").write_text((SRC / "app" / "schemas" / "schemas.py").read_text())
    (DIST / "api").mkdir(parents=True, exist_ok=True)
    (DIST / "api" / "index.py").write_text((SRC / "api" / "index.py").read_text())
    (DIST / "requirements.txt").write_text((SRC / "requirements.txt").read_text())
    (DIST / "vercel.json").write_text((SRC / "vercel.json").read_text())


if __name__ == "__main__":
    (DIST / "app").mkdir(parents=True, exist_ok=True)
    (DIST / "app" / "models").mkdir(parents=True, exist_ok=True)
    build_core_bundle()
    build_routers_bundle()
    build_models()
    build_main()
    copy_static()
    print("done")
