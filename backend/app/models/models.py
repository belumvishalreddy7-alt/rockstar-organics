"""
Database models for the Rockstar Organics platform.

This is a deliberately scoped "deep vertical slice" of the full specification:
every table here is real, migrated, and used end-to-end by the API and tests.
Tables are grouped by domain with comments. Enums are implemented as plain
string columns with CHECK-style validation in the Pydantic schemas /
service layer (kept portable between SQLite dev and PostgreSQL production).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


# ---------------------------------------------------------------------------
# Users, roles, auth
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # active | pending | suspended | rejected | disabled
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # Bumped every time the password changes (registration, reset, change).
    # Embedded into the session token so a session issued before a password
    # change is rejected even though itsdangerous tokens are otherwise
    # stateless - this is what makes "reset your password" actually log out
    # anyone who had a stolen session.
    password_changed_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    farmer_profile: Mapped["FarmerProfile"] = relationship(back_populates="user", uselist=False)
    dealer_profile: Mapped["DealerProfile"] = relationship(back_populates="user", uselist=False)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Farmer profile
# ---------------------------------------------------------------------------

class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), unique=True, nullable=False)
    state: Mapped[str] = mapped_column(String(100), default="Telangana")
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mandal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    village: Mapped[str | None] = mapped_column(String(150), nullable=True)
    pin_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    farm_size: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    farm_size_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    main_crops: Mapped[str | None] = mapped_column(String(255), nullable=True)
    irrigation_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(20), default="en")
    preferred_contact_method: Mapped[str] = mapped_column(String(20), default="phone")
    public_data_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="farmer_profile")


# ---------------------------------------------------------------------------
# Dealer applications, dealer profiles, service areas
# ---------------------------------------------------------------------------

class DealerApplication(Base):
    __tablename__ = "dealer_applications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    reference_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    alternate_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    village_or_town: Mapped[str | None] = mapped_column(String(150), nullable=True)
    mandal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), default="Telangana")
    pin_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    years_in_business: Mapped[int | None] = mapped_column(Integer, nullable=True)
    main_crops_served: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_territory: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_capability: Mapped[bool] = mapped_column(Boolean, default=False)
    farmer_support_interest: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="new")
    # new | under_review | information_required | contacted | on_hold | approved | rejected | withdrawn
    reviewer_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class DealerProfile(Base):
    __tablename__ = "dealer_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), unique=True, nullable=False)
    application_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("dealer_applications.id"), nullable=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    public_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    public_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    directory_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    farmer_case_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    show_public_phone: Mapped[bool] = mapped_column(Boolean, default=False)
    show_public_email: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    capacity: Mapped[int] = mapped_column(Integer, default=10)
    last_activity_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="dealer_profile")
    service_areas: Mapped[list["DealerServiceArea"]] = relationship(back_populates="dealer", cascade="all, delete-orphan")


class DealerServiceArea(Base):
    __tablename__ = "dealer_service_areas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    dealer_id: Mapped[str] = mapped_column(String(32), ForeignKey("dealer_profiles.id"), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    mandal: Mapped[str | None] = mapped_column(String(100), nullable=True)

    dealer: Mapped["DealerProfile"] = relationship(back_populates="service_areas")
    __table_args__ = (UniqueConstraint("dealer_id", "district", "mandal", name="uq_dealer_area"),)


class DealerProductAvailability(Base):
    __tablename__ = "dealer_product_availability"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    dealer_id: Mapped[str] = mapped_column(String(32), ForeignKey("dealer_profiles.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(32), ForeignKey("products.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # available|limited|unavailable|unknown
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    __table_args__ = (UniqueConstraint("dealer_id", "product_id", name="uq_dealer_product"),)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("product_categories.id"), nullable=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("product_categories.id"), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    full_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_crops: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crop_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    application_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dosage_value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dosage_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pack_sizes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    precautions: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulatory_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    seo_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    # draft|in_review|approved|published|unpublished|archived|rejected
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    updated_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    images: Mapped[list["ProductImage"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    reviews: Mapped[list["ProductReview"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(String(32), ForeignKey("products.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped["Product"] = relationship(back_populates="images")


class ProductReview(Base):
    __tablename__ = "product_reviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(String(32), ForeignKey("products.id"), nullable=False)
    # Nullable at the DB level for backward compatibility with any existing
    # anonymous reviews (never destructively altered by a migration - see
    # docs/PRODUCTION_CHECKLIST.md), but enforced NOT NULL at the API layer:
    # only an authenticated farmer may submit a new review (see
    # routers/reviews.py), and reviewer_name is derived from the account,
    # never client-supplied free text, so it can't be spoofed to
    # impersonate someone else.
    user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reviewer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|under_review|approved|rejected|spam
    moderator_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    moderator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    product: Mapped["Product"] = relationship(back_populates="reviews")


# ---------------------------------------------------------------------------
# Farmer support cases
# ---------------------------------------------------------------------------

class FarmerSupportCase(Base):
    __tablename__ = "farmer_support_cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    reference_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    farmer_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    crop: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crop_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    mandal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    village: Mapped[str | None] = mapped_column(String(150), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # low|medium|high|urgent
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    assigned_dealer_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("dealer_profiles.id"), nullable=True)
    assigned_field_officer_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    assigned_staff_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    closure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class CaseMessage(Base):
    """A single timeline entry on a support case: a shared message or an
    internal-only staff/dealer note (never shown to the farmer)."""
    __tablename__ = "case_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("farmer_support_cases.id"), nullable=False)
    author_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    event_type: Mapped[str] = mapped_column(String(30), default="message")
    # message | status_change | assignment | attachment | visit_event
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Field visits
# ---------------------------------------------------------------------------

class FieldVisit(Base):
    __tablename__ = "field_visits"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    reference_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("farmer_support_cases.id"), nullable=False)
    farmer_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False)
    assigned_officer_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    requested_date: Mapped[dt.date | None] = mapped_column(DateTime, nullable=True)
    scheduled_start: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_end: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="requested")
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    farmer_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    visit_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


# ---------------------------------------------------------------------------
# Enquiries
# ---------------------------------------------------------------------------

class Enquiry(Base):
    __tablename__ = "enquiries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    reference_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    enquiry_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("products.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new")
    assigned_staff_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


# ---------------------------------------------------------------------------
# Follow-up tasks, notifications, announcements, knowledge, settings, audit
# ---------------------------------------------------------------------------

class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    due_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    recipient_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    delivery_status: Mapped[str] = mapped_column(String(20), default="delivered")
    # delivered (in-app) | disabled (external channel not configured) | failed
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    announcement_type: Mapped[str] = mapped_column(String(30), default="general")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    publish_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crops: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(150), nullable=True)
    author_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default="This article is general information, reviewed by Rockstar Organics staff. "
        "It is not a substitute for a site visit or a diagnosis by a qualified agronomist.",
    )
    published_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    last_reviewed_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class CompanySetting(Base):
    """Key/value store for editable company settings and site content."""
    __tablename__ = "company_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    actor_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, index=True)


class MediaRecord(Base):
    """Generic file record backing product images/labels, farmer case
    attachments, and dealer documents. `entity_type`/`entity_id` link it to
    the owning record; `is_public` controls whether it is ever served
    through the public (vs. private, permission-checked) file route."""
    __tablename__ = "media_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    purpose: Mapped[str] = mapped_column(String(30), default="general")
    # general | product_image | product_label | case_attachment | dealer_document
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# OTP-gated signup
# ---------------------------------------------------------------------------

class OtpCode(Base):
    """A short-lived, hashed one-time code for the /auth/signup ->
    /auth/verify-otp flow. Only the hash is stored (same pattern as
    PasswordResetToken) so a database read alone never discloses a usable
    code."""
    __tablename__ = "otp_codes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), default="signup")  # signup | login_2fa (future)
    # The pending account payload (full_name, phone, role, hashed password)
    # is held here until the code is verified, so no User row exists until
    # the email address has actually been proven reachable.
    pending_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pending_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pending_password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    pending_role: Mapped[str] = mapped_column(String(32), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Distributors
# ---------------------------------------------------------------------------

class DistributorApplication(Base):
    """Mirrors DealerApplication's registration -> verification -> approval
    -> activation workflow, for the Distributor role added by the
    real-world content spec."""
    __tablename__ = "distributor_applications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    reference_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    alternate_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    territory: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(100), default="Telangana")
    pin_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    years_in_business: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warehouse_capacity_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="new")
    # new | under_review | information_required | contacted | on_hold | approved | rejected | withdrawn
    reviewer_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class DistributorProfile(Base):
    __tablename__ = "distributor_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), unique=True, nullable=False)
    application_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("distributor_applications.id"), nullable=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    territory: Mapped[str] = mapped_column(String(255), nullable=False)
    public_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    public_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    last_activity_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship()


class DistributorStock(Base):
    """A distributor's declared stock level for a product - coarser-grained
    than dealer per-product availability (available/limited/unavailable),
    since distributors deal in bulk/warehouse quantities rather than
    shelf-level stock."""
    __tablename__ = "distributor_stock"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    distributor_id: Mapped[str] = mapped_column(String(32), ForeignKey("distributor_profiles.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(32), ForeignKey("products.id"), nullable=False)
    quantity_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    # available | limited | unavailable | unknown
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (UniqueConstraint("distributor_id", "product_id", name="uq_distributor_product"),)


# ---------------------------------------------------------------------------
# Company certificates & official documents
# ---------------------------------------------------------------------------

class CompanyDocument(Base):
    """Company certificates and official documents. Uploading a file does
    NOT make it verified or public - both `verification_status` and
    `is_published` must be explicitly set by an authorized staff member,
    per the spec's "Uploaded -> Under Review -> Verified -> Published"
    lifecycle."""
    __tablename__ = "company_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # company_certificate | registration_document | manufacturing_certificate |
    # quality_certificate | compliance_document | licence | product_certificate | other
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    media_id: Mapped[str] = mapped_column(String(32), ForeignKey("media_records.id"), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), default="uploaded")
    # uploaded | under_review | verified | rejected
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    # Extends the uploaded -> under_review -> verified/rejected -> published
    # lifecycle above with an explicit approval gate before publish, and
    # full submitted/rejected/approved/archived provenance - see
    # docs/SECURITY.md "Certificate verification workflow". Additive to the
    # fields above rather than replacing them, so existing verification_status/
    # is_published consumers keep working unchanged.
    submitted_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    published_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


# ---------------------------------------------------------------------------
# Agriculture photo gallery
# ---------------------------------------------------------------------------

class AgriculturePhoto(Base):
    """Agricultural photo gallery entries. Per the spec's real-world photo
    principles: never invent location/crop/date/photographer - each of
    those fields is nullable and the frontend renders "Information pending
    verification." when unset, rather than the backend fabricating a
    value."""
    __tablename__ = "agriculture_photos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # farmers | farms | fields | crops | product_application | dealer_network |
    # distributor_network | field_visits | agricultural_activities |
    # company_facilities | manufacturing | research | community_activities
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crop: Mapped[str | None] = mapped_column(String(150), nullable=True)
    photo_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    photographer_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    usage_rights_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_rights_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    alt_text: Mapped[str] = mapped_column(String(300), nullable=False)
    media_id: Mapped[str] = mapped_column(String(32), ForeignKey("media_records.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # draft | submitted | under_review | approved | rejected | published | archived
    uploaded_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    submitted_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    published_by_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
