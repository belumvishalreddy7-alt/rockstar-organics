from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import PRODUCT_MANAGERS
from app.models.models import ProductCategory, User
from app.schemas.schemas import CategoryCreate

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("/public")
def public_categories(db: Session = Depends(get_db)):
    cats = db.query(ProductCategory).all()
    return [{"id": c.id, "name": c.name, "slug": c.slug} for c in cats]


@router.post("")
def create_category(payload: CategoryCreate, user: User = Depends(require_roles(*PRODUCT_MANAGERS, "super_admin")), db: Session = Depends(get_db)):
    name, slug = payload.name, payload.slug
    if db.query(ProductCategory).filter(ProductCategory.slug == slug).first():
        raise HTTPException(status_code=400, detail="A category with this slug already exists.")
    c = ProductCategory(name=name, slug=slug)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "name": c.name, "slug": c.slug}
