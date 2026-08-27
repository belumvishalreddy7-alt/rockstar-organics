"""Human-friendly reference number generation (case/visit/enquiry/etc)."""
import datetime as dt
import random


def generate_reference(prefix: str) -> str:
    stamp = dt.datetime.utcnow().strftime("%y%m%d")
    suffix = "".join(random.choices("0123456789", k=5))
    return f"{prefix}-{stamp}-{suffix}"
