import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.permissions import ROLE_ADMIN, ROLE_SUPER_ADMIN
from app.models.models import AuditLog, DealerApplication, FarmerSupportCase, Product, User

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

EXPORTABLE = {
    "products": (Product, ["id", "sku", "name", "status", "created_at"]),
    "dealer_applications": (DealerApplication, ["id", "reference_number", "business_name", "district", "status", "created_at"]),
    "farmer_cases": (FarmerSupportCase, ["id", "reference_number", "title", "status", "district", "priority", "created_at"]),
    "audit_logs": (AuditLog, ["id", "actor_id", "action", "entity_type", "entity_id", "summary", "created_at"]),
}


@router.get("/dashboard-metrics")
def dashboard_metrics(user: User = Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN)), db: Session = Depends(get_db)):
    from app.models.models import Enquiry, FieldVisit, FollowUpTask, KnowledgeArticle, Notification, ProductReview

    return {
        "draft_products": db.query(Product).filter(Product.status == "draft").count(),
        "products_in_review": db.query(Product).filter(Product.status == "in_review").count(),
        "published_products": db.query(Product).filter(Product.status == "published").count(),
        "new_dealer_applications": db.query(DealerApplication).filter(DealerApplication.status == "new").count(),
        "open_support_cases": db.query(FarmerSupportCase).filter(FarmerSupportCase.status.notin_(["resolved", "closed", "cancelled", "spam"])).count(),
        "high_priority_cases": db.query(FarmerSupportCase).filter(FarmerSupportCase.priority == "high").count(),
        "upcoming_field_visits": db.query(FieldVisit).filter(FieldVisit.status.in_(["scheduled", "confirmed"])).count(),
        "pending_reviews": db.query(ProductReview).filter(ProductReview.status == "pending").count(),
        "open_enquiries": db.query(Enquiry).filter(Enquiry.status.notin_(["resolved", "closed", "cancelled", "spam"])).count(),
        "overdue_tasks": db.query(FollowUpTask).filter(FollowUpTask.status.in_(["open", "in_progress"])).count(),
        "published_knowledge_articles": db.query(KnowledgeArticle).filter(KnowledgeArticle.status == "published").count(),
        "failed_notifications": db.query(Notification).filter(Notification.delivery_status == "failed").count(),
    }


@router.get("/export/{report_key}")
def export_csv(report_key: str, user: User = Depends(require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN)), db: Session = Depends(get_db)):
    if report_key not in EXPORTABLE:
        return StreamingResponse(io.StringIO("invalid report\n"), media_type="text/csv", status_code=400)
    model, columns = EXPORTABLE[report_key]
    rows = db.query(model).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for r in rows:
        writer.writerow([getattr(r, c) for c in columns])
    record_audit(db, actor_id=user.id, action="report.export", entity_type=report_key, entity_id=None,
                 summary=f"Exported {report_key} CSV ({len(rows)} rows)")
    db.commit()
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                              headers={"Content-Disposition": f"attachment; filename={report_key}.csv"})
