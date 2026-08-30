"""Pydantic request/response schemas. Backend validation here is
authoritative; frontend validation is a convenience only.

Every free-text field carries an explicit max_length: an unbounded Text
column plus an unbounded request field is a storage-exhaustion vector (one
client can otherwise post megabyte-scale strings all day), so the caps
here are the actual enforcement point, not just UX guidance.
"""
from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, EmailStr, Field, field_validator

PHONE_RE = re.compile(r"^[6-9]\d{9}$")
PIN_RE = re.compile(r"^\d{6}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SEVERITY_VALUES = {"low", "medium", "high", "urgent"}
ENQUIRY_TYPE_VALUES = {"general", "product", "dealer", "bulk_purchase", "business_partnership",
                       "farmer_support_followup", "website_issue", "privacy_request"}


class RegisterFarmerRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str
    password: str = Field(min_length=1, max_length=256)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    must_change_password: bool

    class Config:
        from_attributes = True


class FarmerProfileUpdate(BaseModel):
    district: str | None = Field(default=None, max_length=100)
    mandal: str | None = Field(default=None, max_length=100)
    village: str | None = Field(default=None, max_length=150)
    pin_code: str | None = None
    farm_size: float | None = None
    farm_size_unit: str | None = Field(default=None, max_length=20)
    main_crops: str | None = Field(default=None, max_length=255)
    irrigation_type: str | None = Field(default=None, max_length=50)
    preferred_language: str | None = Field(default=None, max_length=20)
    preferred_contact_method: str | None = Field(default=None, max_length=20)
    public_data_opt_in: bool | None = None

    @field_validator("pin_code")
    @classmethod
    def valid_pin(cls, v):
        if v and not PIN_RE.match(v):
            raise ValueError("Enter a valid 6-digit PIN code.")
        return v


class DealerApplicationCreate(BaseModel):
    contact_person: str = Field(min_length=1, max_length=255)
    business_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str
    alternate_phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    village_or_town: str | None = Field(default=None, max_length=150)
    mandal: str | None = Field(default=None, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    state: str = Field(default="Telangana", max_length=100)
    pin_code: str | None = None
    gstin: str | None = Field(default=None, max_length=20)
    years_in_business: int | None = Field(default=None, ge=0, le=200)
    main_crops_served: str | None = Field(default=None, max_length=255)
    requested_territory: str | None = Field(default=None, max_length=255)
    delivery_capability: bool = False
    farmer_support_interest: bool = False
    notes: str | None = Field(default=None, max_length=2000)
    consent_given: bool

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return v

    @field_validator("pin_code")
    @classmethod
    def valid_pin(cls, v):
        if v and not PIN_RE.match(v):
            raise ValueError("Enter a valid 6-digit PIN code.")
        return v

    @field_validator("consent_given")
    @classmethod
    def must_consent(cls, v):
        if not v:
            raise ValueError("Consent is required to submit a dealer application.")
        return v


class DealerApplicationDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    category_id: str | None = None
    product_type: str | None = Field(default=None, max_length=60)
    short_description: str | None = Field(default=None, max_length=500)
    full_description: str | None = Field(default=None, max_length=10000)
    benefits: str | None = Field(default=None, max_length=5000)
    recommended_crops: str | None = Field(default=None, max_length=255)
    crop_stage: str | None = Field(default=None, max_length=100)
    application_method: str | None = Field(default=None, max_length=255)
    dosage_value: str | None = Field(default=None, max_length=50)
    dosage_unit: str | None = Field(default=None, max_length=30)
    pack_sizes: str | None = Field(default=None, max_length=255)
    precautions: str | None = Field(default=None, max_length=5000)
    regulatory_notes: str | None = Field(default=None, max_length=5000)
    active_ingredients: str | None = Field(default=None, max_length=5000)
    nutrient_content: str | None = Field(default=None, max_length=5000)
    concentration: str | None = Field(default=None, max_length=100)
    formulation: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=100)
    physical_form: str | None = Field(default=None, max_length=100)
    technical_specifications: str | None = Field(default=None, max_length=5000)

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, v):
        if not SLUG_RE.match(v):
            raise ValueError("Slug must be lowercase letters, numbers, and hyphens only.")
        return v


class ProductUpdate(ProductCreate):
    pass


class ProductStatusChange(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


PACK_SIZE_AVAILABILITY_VALUES = {"available", "out_of_stock", "discontinued"}


class ProductPackSizeCreate(BaseModel):
    quantity: str = Field(min_length=1, max_length=30)
    unit: str = Field(min_length=1, max_length=20)
    packaging_type: str | None = Field(default=None, max_length=60)
    sku: str | None = Field(default=None, max_length=60)
    price: float | None = Field(default=None, ge=0)
    availability_status: str = "available"

    @field_validator("availability_status")
    @classmethod
    def valid_availability(cls, v):
        if v not in PACK_SIZE_AVAILABILITY_VALUES:
            raise ValueError(f"availability_status must be one of: {', '.join(sorted(PACK_SIZE_AVAILABILITY_VALUES))}.")
        return v


class ProductCropCreate(BaseModel):
    crop_name: str = Field(min_length=1, max_length=100)
    crop_category: str | None = Field(default=None, max_length=100)
    target_use: str | None = Field(default=None, max_length=255)
    application_stage: str | None = Field(default=None, max_length=100)


CLAIM_CATEGORY_VALUES = {"benefit", "technical", "crop", "quality", "certification"}


class ProductClaimCreate(BaseModel):
    claim_text: str = Field(min_length=1, max_length=2000)
    category: str = "benefit"
    source_evidence: str | None = Field(default=None, max_length=2000)

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in CLAIM_CATEGORY_VALUES:
            raise ValueError(f"category must be one of: {', '.join(sorted(CLAIM_CATEGORY_VALUES))}.")
        return v


class ProductCertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    issuing_organization: str | None = Field(default=None, max_length=255)
    certificate_number: str | None = Field(default=None, max_length=100)
    issue_date: dt.datetime | None = None
    expiry_date: dt.datetime | None = None
    media_id: str | None = None


PRODUCT_DOCUMENT_TYPE_VALUES = {
    "technical_data_sheet", "specification", "safety_data_sheet", "certificate",
    "registration", "label", "brochure", "catalogue", "regulatory", "other",
}


class ProductDocumentCreate(BaseModel):
    document_type: str
    title: str = Field(min_length=1, max_length=255)
    version: str | None = Field(default=None, max_length=30)
    issue_date: dt.datetime | None = None
    expiry_date: dt.datetime | None = None
    document_number: str | None = Field(default=None, max_length=100)
    media_id: str

    @field_validator("document_type")
    @classmethod
    def valid_document_type(cls, v):
        if v not in PRODUCT_DOCUMENT_TYPE_VALUES:
            raise ValueError(f"document_type must be one of: {', '.join(sorted(PRODUCT_DOCUMENT_TYPE_VALUES))}.")
        return v


VERIFICATION_STATUS_VALUES = {"pending", "verified", "rejected"}


class VerificationStatusChange(BaseModel):
    verification_status: str

    @field_validator("verification_status")
    @classmethod
    def valid_status(cls, v):
        if v not in VERIFICATION_STATUS_VALUES:
            raise ValueError(f"verification_status must be one of: {', '.join(sorted(VERIFICATION_STATUS_VALUES))}.")
        return v


class SupportCaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=5000)
    crop: str | None = Field(default=None, max_length=100)
    crop_stage: str | None = Field(default=None, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    mandal: str | None = Field(default=None, max_length=100)
    village: str | None = Field(default=None, max_length=150)
    severity: str = "medium"

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, v):
        if v not in SEVERITY_VALUES:
            raise ValueError(f"Severity must be one of: {', '.join(sorted(SEVERITY_VALUES))}.")
        return v


class CaseMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    is_private: bool = False


class CaseAssignRequest(BaseModel):
    dealer_id: str | None = None
    field_officer_id: str | None = None
    staff_id: str | None = None


class CaseStatusChange(BaseModel):
    status: str
    note: str | None = Field(default=None, max_length=2000)


class FieldVisitCreate(BaseModel):
    case_id: str
    requested_date: dt.datetime | None = None
    purpose: str | None = Field(default=None, max_length=500)
    farmer_instructions: str | None = Field(default=None, max_length=2000)


class FieldVisitSchedule(BaseModel):
    assigned_officer_id: str
    scheduled_start: dt.datetime
    scheduled_end: dt.datetime
    internal_instructions: str | None = Field(default=None, max_length=2000)


class FieldVisitComplete(BaseModel):
    visit_summary: str = Field(min_length=1, max_length=5000)
    follow_up_required: bool = False


class EnquiryCreate(BaseModel):
    enquiry_type: str
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    district: str | None = Field(default=None, max_length=100)
    product_id: str | None = None
    message: str = Field(min_length=1, max_length=5000)
    # Consent must be explicitly given - it does not default to true.
    consent_given: bool = False

    @field_validator("enquiry_type")
    @classmethod
    def valid_type(cls, v):
        if v not in ENQUIRY_TYPE_VALUES:
            raise ValueError(f"Enquiry type must be one of: {', '.join(sorted(ENQUIRY_TYPE_VALUES))}.")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def blank_email_is_none(cls, v):
        # The frontend's optional email field submits "" rather than
        # omitting the key when left blank; without this, Pydantic's
        # EmailStr validator rejects "" as "not a valid email address" even
        # though the field is optional. An empty/whitespace-only value is
        # treated the same as not having been provided at all.
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if v and not PHONE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return v

    @field_validator("consent_given")
    @classmethod
    def must_consent(cls, v):
        if not v:
            raise ValueError("Consent is required to submit an enquiry.")
        return v


class ReviewCreate(BaseModel):
    # No reviewer_name here (deliberately) - it used to be free client-
    # supplied text, which let a logged-in farmer post under any name they
    # typed. The submitting farmer's own account name is used instead
    # (see routers/reviews.py) so a review can never claim to be from
    # someone it isn't.
    rating: int
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("rating")
    @classmethod
    def valid_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5.")
        return v


class ReviewModeration(BaseModel):
    status: str
    moderator_notes: str | None = Field(default=None, max_length=2000)


class CompanySettingUpdate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str | None = Field(default=None, max_length=5000)


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1, max_length=10000)
    announcement_type: str = "general"
    featured: bool = False
    publish_date: dt.datetime | None = None
    expiry_date: dt.datetime | None = None

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, v):
        if not SLUG_RE.match(v):
            raise ValueError("Slug must be lowercase letters, numbers, and hyphens only.")
        return v


class KnowledgeArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1, max_length=20000)
    topic: str | None = Field(default=None, max_length=100)
    crops: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=150)

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, v):
        if not SLUG_RE.match(v):
            raise ValueError("Slug must be lowercase letters, numbers, and hyphens only.")
        return v


class FollowUpTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    related_entity_type: str | None = Field(default=None, max_length=50)
    related_entity_id: str | None = None
    assigned_user_id: str | None = None
    priority: str = "normal"
    due_date: dt.datetime | None = None


# ---------------------------------------------------------------------------
# OTP-gated signup
# ---------------------------------------------------------------------------

SIGNUP_ROLE_VALUES = {"farmer", "dealer_applicant", "distributor_applicant"}
# dealer_applicant/distributor_applicant just create a farmer-equivalent
# base account that then goes through the existing dealer/distributor
# application workflow - this endpoint issues no dealer/distributor role
# directly, since that role is only ever granted on application approval.


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str
    password: str = Field(min_length=1, max_length=256)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return v


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=10)


# ---------------------------------------------------------------------------
# Distributors
# ---------------------------------------------------------------------------

class DistributorApplicationCreate(BaseModel):
    contact_person: str = Field(min_length=1, max_length=255)
    business_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str
    alternate_phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    territory: str = Field(min_length=1, max_length=255)
    state: str = Field(default="Telangana", max_length=100)
    pin_code: str | None = None
    gstin: str | None = Field(default=None, max_length=20)
    years_in_business: int | None = None
    warehouse_capacity_notes: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    consent_given: bool = False

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return v

    @field_validator("consent_given")
    @classmethod
    def must_consent(cls, v):
        if not v:
            raise ValueError("Consent is required to submit a distributor application.")
        return v


class DistributorApplicationDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Company certificates & official documents
# ---------------------------------------------------------------------------

COMPANY_DOCUMENT_TYPES = {
    "company_certificate", "registration_document", "manufacturing_certificate",
    "quality_certificate", "compliance_document", "licence", "product_certificate", "other",
}


class CompanyDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    document_type: str
    media_id: str
    reference_number: str | None = Field(default=None, max_length=100)
    issuing_authority: str | None = Field(default=None, max_length=255)
    issue_date: dt.datetime | None = None
    expiry_date: dt.datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("document_type")
    @classmethod
    def valid_type(cls, v):
        if v not in COMPANY_DOCUMENT_TYPES:
            raise ValueError(f"Document type must be one of: {', '.join(sorted(COMPANY_DOCUMENT_TYPES))}.")
        return v


class CompanyDocumentReview(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Agriculture photo gallery
# ---------------------------------------------------------------------------

AGRICULTURE_PHOTO_CATEGORIES = {
    "farmers", "farms", "fields", "crops", "product_application", "dealer_network",
    "distributor_network", "field_visits", "agricultural_activities",
    "company_facilities", "manufacturing", "research", "community_activities",
}


class AgriculturePhotoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    caption: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=3000)
    category: str
    location: str | None = Field(default=None, max_length=255)
    crop: str | None = Field(default=None, max_length=150)
    photo_date: dt.datetime | None = None
    photographer_source: str | None = Field(default=None, max_length=255)
    usage_rights_verified: bool = False
    usage_rights_notes: str | None = Field(default=None, max_length=500)
    alt_text: str = Field(min_length=1, max_length=300)
    media_id: str

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in AGRICULTURE_PHOTO_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(sorted(AGRICULTURE_PHOTO_CATEGORIES))}.")
        return v


class AgriculturePhotoStatusChange(BaseModel):
    rejection_reason: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Dealer / distributor self-service profile updates
# ---------------------------------------------------------------------------
# All fields optional so a partial update (only the fields the client sent)
# is possible via `.model_dump(exclude_unset=True)` in the router - but every
# field that does arrive is still validated and length-capped, unlike the
# raw `dict` these replaced.


IRRIGATION_TYPE_VALUES = {"rainfed", "borewell", "canal", "drip", "sprinkler", "tank", "other"}
LANGUAGE_VALUES = {"en", "te", "hi"}
CONTACT_METHOD_VALUES = {"phone", "sms", "whatsapp", "email"}


class FarmerProfileUpdate(BaseModel):
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    mandal: str | None = Field(default=None, max_length=100)
    village: str | None = Field(default=None, max_length=150)
    pin_code: str | None = None
    farm_size: float | None = Field(default=None, ge=0, le=100000)
    farm_size_unit: str | None = Field(default=None, max_length=20)
    main_crops: str | None = Field(default=None, max_length=255)
    irrigation_type: str | None = None
    preferred_language: str | None = None
    preferred_contact_method: str | None = None
    public_data_opt_in: bool | None = None

    @field_validator("pin_code")
    @classmethod
    def valid_pin(cls, v):
        if v and not PIN_RE.match(v):
            raise ValueError("Enter a valid 6-digit PIN code.")
        return v

    @field_validator("irrigation_type")
    @classmethod
    def valid_irrigation(cls, v):
        if v and v not in IRRIGATION_TYPE_VALUES:
            raise ValueError(f"irrigation_type must be one of: {', '.join(sorted(IRRIGATION_TYPE_VALUES))}.")
        return v

    @field_validator("preferred_language")
    @classmethod
    def valid_language(cls, v):
        if v and v not in LANGUAGE_VALUES:
            raise ValueError(f"preferred_language must be one of: {', '.join(sorted(LANGUAGE_VALUES))}.")
        return v

    @field_validator("preferred_contact_method")
    @classmethod
    def valid_contact_method(cls, v):
        if v and v not in CONTACT_METHOD_VALUES:
            raise ValueError(f"preferred_contact_method must be one of: {', '.join(sorted(CONTACT_METHOD_VALUES))}.")
        return v


class DealerProfileUpdate(BaseModel):
    directory_opt_in: bool | None = None
    farmer_case_opt_in: bool | None = None
    show_public_phone: bool | None = None
    show_public_email: bool | None = None
    public_phone: str | None = Field(default=None, max_length=20)
    public_email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)

    @field_validator("public_phone")
    @classmethod
    def valid_public_phone(cls, v):
        if v and not PHONE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return v


class DistributorProfileUpdate(BaseModel):
    territory: str | None = Field(default=None, min_length=1, max_length=255)
    public_phone: str | None = Field(default=None, max_length=20)
    public_email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)

    @field_validator("public_phone")
    @classmethod
    def valid_public_phone(cls, v):
        if v and not PHONE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return v


# ---------------------------------------------------------------------------
# Staff invitations
# ---------------------------------------------------------------------------


class StaffInviteRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=30)


# ---------------------------------------------------------------------------
# Product categories
# ---------------------------------------------------------------------------


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    slug: str = Field(min_length=1, max_length=150)

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, v):
        if not SLUG_RE.match(v):
            raise ValueError("Slug must be lowercase letters, numbers, and hyphens only.")
        return v


# ---------------------------------------------------------------------------
# Corporate content CMS (Leadership, Manufacturing, R&D, Quality & Safety,
# Sustainability) - shared verification/approval/publication fields, plus
# one Create/Out pair per entity for the fields that differ.
# ---------------------------------------------------------------------------

CORPORATE_SECTIONS = {"leadership", "manufacturing", "research_development", "quality_safety", "sustainability"}


class WorkflowActionNote(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class VerifiableFieldsOut(BaseModel):
    id: str
    status: str
    source_reference: str | None
    verification_notes: str | None
    rejection_reason: str | None
    created_by_id: str | None
    updated_by_id: str | None
    submitted_by_id: str | None
    submitted_at: dt.datetime | None
    reviewer_id: str | None
    verified_at: dt.datetime | None
    approved_by_id: str | None
    approved_at: dt.datetime | None
    published_by_id: str | None
    published_at: dt.datetime | None
    version: int
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class CompanyPageContentUpdate(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)
    source_reference: str | None = Field(default=None, max_length=2000)

    @field_validator("fields")
    @classmethod
    def cap_field_values(cls, v):
        for key, value in v.items():
            if len(key) > 100 or len(value) > 20000:
                raise ValueError("Field name or value is too long.")
        return v


class CompanyPageContentOut(VerifiableFieldsOut):
    section: str
    fields: dict[str, str]


class LeadershipProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    position: str = Field(min_length=1, max_length=255)
    biography: str | None = Field(default=None, max_length=8000)
    photo_media_id: str | None = None
    responsibilities: str | None = Field(default=None, max_length=4000)
    experience: str | None = Field(default=None, max_length=4000)
    education: str | None = Field(default=None, max_length=2000)
    profile_url: str | None = Field(default=None, max_length=500)
    joining_date: dt.datetime | None = None
    sort_order: int = 0
    source_reference: str | None = Field(default=None, max_length=2000)


class LeadershipProfileOut(VerifiableFieldsOut):
    full_name: str
    position: str
    biography: str | None
    photo_media_id: str | None
    responsibilities: str | None
    experience: str | None
    education: str | None
    profile_url: str | None
    joining_date: dt.datetime | None
    sort_order: int


class ManufacturingFacilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    facility_type: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=2000)
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = Field(default=None, max_length=8000)
    capabilities: str | None = Field(default=None, max_length=4000)
    certifications_text: str | None = Field(default=None, max_length=2000)
    capacity: str | None = Field(default=None, max_length=255)
    established_date: dt.datetime | None = None
    contact_info: str | None = Field(default=None, max_length=500)
    source_reference: str | None = Field(default=None, max_length=2000)


class ManufacturingFacilityOut(VerifiableFieldsOut):
    name: str
    facility_type: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    description: str | None
    capabilities: str | None
    certifications_text: str | None
    capacity: str | None
    established_date: dt.datetime | None
    contact_info: str | None


class ResearchFacilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    facility_type: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=8000)
    capabilities: str | None = Field(default=None, max_length=4000)
    equipment_info: str | None = Field(default=None, max_length=4000)
    source_reference: str | None = Field(default=None, max_length=2000)


class ResearchFacilityOut(VerifiableFieldsOut):
    name: str
    facility_type: str | None
    location: str | None
    description: str | None
    capabilities: str | None
    equipment_info: str | None


class ResearchAreaCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    image_media_id: str | None = None
    sort_order: int = 0
    source_reference: str | None = Field(default=None, max_length=2000)


class ResearchAreaOut(VerifiableFieldsOut):
    title: str
    description: str | None
    image_media_id: str | None
    sort_order: int


class CertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    certificate_number: str | None = Field(default=None, max_length=100)
    issuing_organization: str | None = Field(default=None, max_length=255)
    issue_date: dt.datetime | None = None
    expiry_date: dt.datetime | None = None
    document_media_id: str | None = None
    scope: str | None = Field(default=None, max_length=2000)
    source_reference: str | None = Field(default=None, max_length=2000)


class CertificationOut(VerifiableFieldsOut):
    name: str
    certificate_number: str | None
    issuing_organization: str | None
    issue_date: dt.datetime | None
    expiry_date: dt.datetime | None
    document_media_id: str | None
    scope: str | None


class SustainabilityInitiativeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=8000)
    category: str | None = Field(default=None, max_length=100)
    start_date: dt.datetime | None = None
    measurable_results: str | None = Field(default=None, max_length=2000)
    source_reference: str | None = Field(default=None, max_length=2000)


class SustainabilityInitiativeOut(VerifiableFieldsOut):
    title: str
    description: str | None
    category: str | None
    start_date: dt.datetime | None
    measurable_results: str | None


# ---------------------------------------------------------------------------
# Staff (employee) applications - a public applicant may only request one of
# these three positions; admin/super_admin are never offered here and can
# only ever be granted by an existing super_admin at approval time (see
# StaffApplicationApprove.role, validated against STAFF_ROLES generally,
# and require_roles(ROLE_SUPER_ADMIN) for granting super_admin specifically).
# ---------------------------------------------------------------------------

STAFF_POSITION_VALUES = {"content_manager", "sales_manager", "field_officer"}


class StaffApplicationCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str
    position_applied_for: str
    notes: str | None = Field(default=None, max_length=2000)
    consent_given: bool

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return v

    @field_validator("position_applied_for")
    @classmethod
    def valid_position(cls, v):
        if v not in STAFF_POSITION_VALUES:
            raise ValueError(f"position_applied_for must be one of: {', '.join(sorted(STAFF_POSITION_VALUES))}.")
        return v


class StaffApplicationDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class StaffApplicationApprove(BaseModel):
    role: str = Field(min_length=1, max_length=30)
