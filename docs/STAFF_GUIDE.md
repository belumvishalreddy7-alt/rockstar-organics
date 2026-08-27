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

## Reports

Staff → Overview shows live dashboard metrics computed directly from the
database. CSV exports are available via `/api/reports/export/{report_key}`
for products, dealer applications, farmer cases, and audit logs
(Administrator/Super Administrator only), and every export is itself
recorded in the audit log.
