# Role and Permission Guide

Enforcement is server-side (`app/core/deps.py::require_roles`, and the
permission sets in `app/core/permissions.py`); the frontend only hides UI
for convenience and must never be relied on for security.

| Role | Can | Cannot |
|---|---|---|
| **Super Administrator** | Everything Administrator can, plus: create other Super Administrators, permanently delete products, view all audit logs. | — |
| **Administrator** | Manage products, dealer applications, farmer cases, reviews, company settings, staff accounts (except granting Super Administrator). | Grant Super Administrator role. |
| **Content Manager** | Create/edit products, manage reviews, would manage announcements/knowledge in a fuller build. | Manage staff, dealer applications, security settings. |
| **Sales Manager** | Review/approve/reject dealer applications, assign and manage farmer support cases, view dealer matches. | Change product technical fields (in this build, product edit is shared with Content Manager/Admin — see Known Limitations), manage staff security. |
| **Field Officer** | View/manage assigned farmer cases, schedule and complete field visits. | Approve dealers, publish products, change staff roles. |
| **Dealer** | Manage own profile, service areas, directory/case opt-ins, product availability, respond to assigned cases. | Approve themselves, edit products, view other dealers' data or unassigned cases. |
| **Farmer** | Register, manage own profile, submit/view own support cases, request field visits, submit reviews on published products. | View another farmer's case, see private staff/dealer notes, approve product claims. |
| **Public/anonymous** | Browse published products, dealer directory, submit dealer applications and enquiries, register as a farmer. | Access any dashboard or private data. |

## How role checks work

Every protected backend endpoint depends on `require_roles(...)` (see
`app/core/deps.py`), which resolves the current user from the session
cookie and returns HTTP 403 if their role isn't in the allowed set. There is
no endpoint that lets a user change their own `role` field — `role` is
never accepted in any user-editable schema.

## Staff account creation

Staff accounts are never self-registered. The first Super Administrator is
created via `scripts/create_superadmin.py` (a local, password-prompted
script). All further staff accounts are created via
`POST /api/staff/invite`, restricted to Super Administrator/Administrator,
which issues a temporary password and forces a change on first login.
