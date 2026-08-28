# Staff Operations Guide

## Product review

Products move Draft → In Review → Approved → Published (with Unpublished
and Archived as later states, and Rejected as a review outcome). Publishing
is blocked server-side unless category, full description, and precautions
are filled in — this validation is authoritative regardless of what the UI
shows.

## Dealer application review

Review new applications under Staff → Dealer applications. You can mark an
application under review, request information, approve, or reject.
Approval automatically creates the dealer's user account and profile and
issues a temporary password (shown once, on screen — pass it to the dealer
through your own secure channel).

## Farmer case assignment

Staff → Farmer cases shows every case with its status and priority. Use
"View dealer matches" to see a transparently scored list of eligible
dealers (service area match, mandal match, recent activity) and assign
directly from there, or assign a field officer for a site visit.

## Field visits

Field officers schedule visits from a case; the system checks for
scheduling conflicts against that officer's existing visits before
confirming. Completing a visit records a summary and can generate a
follow-up task automatically.

## Escalation

Cases and enquiries can be reassigned at any time by Sales Manager/
Administrator/Super Administrator roles. Every assignment and status change
is written to the audit log with the acting staff member, timestamp, and a
plain-language summary.

## Certificate & document verification

Staff → Certificates & documents. Upload a company certificate/official
document (Content Manager/Administrator/Super Administrator only); this
only stores the file — it is neither verified nor public yet
(`verification_status: uploaded`, `is_published: false`). Move it to
`under_review`, then to `verified` or `rejected`. **Publishing is blocked
server-side unless `verification_status` is `verified`** — this is
enforced by the API, not just hidden in the UI, so there's no way to make
an unverified document public by accident. Only after publishing does it
appear on the public `/certificates` page. Never enter a reference number,
issuing authority, or date you haven't actually confirmed against the real
document — leave the field blank; the public page shows "Information
pending verification." for anything unset rather than a guess.

## Agriculture photo gallery

Staff → Agriculture gallery. Upload an image with an accurate, accessible
alt text (required) and category. **A photo cannot be approved or
published until "Usage rights verified" is checked** — the API rejects the
transition otherwise. Location, crop, date, and photographer/source are
all optional; leave them blank rather than guessing; the public `/gallery`
page shows "Information pending verification." for anything unset. Status
flow: Draft → Under review → Approved → Published (Archived to retire an
image without deleting its record).

## Product review moderation

Staff → Product reviews shows every farmer-submitted review awaiting
moderation (`status: pending`). Approve, reject, or mark spam. Only
`approved` reviews count toward a product's public average rating and
review count (`GET /api/v1/products/public/{slug}`) — a pending or
rejected review is invisible on the public product page. There is no way
to submit a review as staff on a farmer's behalf; reviews always come from
the public review form on a product page.

## Reports

Staff → Overview shows live dashboard metrics computed directly from the
database. CSV exports are available via `/api/reports/export/{report_key}`
for products, dealer applications, farmer cases, and audit logs
(Administrator/Super Administrator only), and every export is itself
recorded in the audit log.
