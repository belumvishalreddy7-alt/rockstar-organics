"""
Development-only demo accounts, per the real-world content spec's
"Development demo accounts" section:

    Super Admin:  admin.demo@example.com      / AdminDemo123!
    Farmer:       farmer.demo@example.com     / FarmerDemo123!
    Dealer:       dealer.demo@example.com     / DealerDemo123!
    Distributor:  distributor.demo@example.com / DistributorDemo123!

These exist purely so a reviewer can log into every portal without running
the full signup/application workflow. They are mockup-only accounts and
this script refuses to run when ENVIRONMENT=production, so they can never
be created in a production deployment by accident.

Usage:
    python -m scripts.seed_demo_accounts          # create
    python -m scripts.seed_demo_accounts --remove  # delete them again
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.permissions import ROLE_ADMIN, ROLE_DEALER, ROLE_DISTRIBUTOR, ROLE_FARMER, ROLE_SUPER_ADMIN
from app.core.security import hash_password
from app.models.models import DealerProfile, DealerServiceArea, DistributorProfile, FarmerProfile, User

DEMO_ACCOUNTS = [
    ("admin.demo@example.com", "AdminDemo123!", ROLE_SUPER_ADMIN, "Demo Super Admin"),
    ("farmer.demo@example.com", "FarmerDemo123!", ROLE_FARMER, "Demo Farmer"),
    ("dealer.demo@example.com", "DealerDemo123!", ROLE_DEALER, "Demo Dealer"),
    ("distributor.demo@example.com", "DistributorDemo123!", ROLE_DISTRIBUTOR, "Demo Distributor"),
]


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", action="store_true", help="Delete the demo accounts instead of creating them.")
    args = parser.parse_args()

    settings = get_settings()
    if settings.ENVIRONMENT == "production":
        print("Refusing to run: ENVIRONMENT=production. Demo accounts must never exist in production.")
        sys.exit(1)

    db = SessionLocal()
    try:
        if args.remove:
            for email, _, _, _ in DEMO_ACCOUNTS:
                user = db.query(User).filter(User.email == email).first()
                if user:
                    db.delete(user)
                    print(f"Removed {email}")
            db.commit()
            return

        for email, password, role, full_name in DEMO_ACCOUNTS:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"{email} already exists, skipping.")
                continue
            user = User(email=email, password_hash=hash_password(password), role=role, full_name=full_name,
                        status="active", email_verified=True)
            db.add(user)
            db.flush()
            if role == ROLE_FARMER:
                db.add(FarmerProfile(user_id=user.id))
            elif role == ROLE_DEALER:
                profile = DealerProfile(user_id=user.id, business_name="Demo Agro Traders", district="Hyderabad",
                                         directory_opt_in=True, farmer_case_opt_in=True)
                db.add(profile)
                db.flush()
                db.add(DealerServiceArea(dealer_id=profile.id, district="Hyderabad", mandal="Serilingampally"))
            elif role == ROLE_DISTRIBUTOR:
                db.add(DistributorProfile(user_id=user.id, business_name="Demo Distribution Co", territory="Ranga Reddy district"))
            print(f"Created {role}: {email} / {password}")
        db.commit()
        print("\nThese are MOCKUP-ONLY accounts. Remove them (--remove) before any production launch.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
