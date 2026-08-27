"""
Seed ONLY required, non-business, non-fake starter data:
- Required company-setting keys (values left empty until staff configure them).
- Nothing else. No products, no dealers, no reviews, no fake counts.

Run with: python -m scripts.seed_required_data
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.models import CompanySetting
from app.routers.settings_router import REQUIRED_KEYS


def run():
    db = SessionLocal()
    try:
        for key in REQUIRED_KEYS:
            if not db.get(CompanySetting, key):
                db.add(CompanySetting(key=key, value=None))
        db.commit()
        print(f"Seeded {len(REQUIRED_KEYS)} required company-setting keys (values empty; configure via admin settings).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
