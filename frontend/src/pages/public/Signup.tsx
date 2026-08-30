import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError, uploadFile } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { PasswordInput } from "../../components/PasswordInput";

type Role = "farmer" | "dealer" | "distributor" | "employee";

const ROLES: { value: Role; label: string; blurb: string }[] = [
  { value: "farmer", label: "Farmer", blurb: "Get an account immediately after a quick email verification." },
  { value: "dealer", label: "Dealer", blurb: "Submits an application for staff review — an account is created only after approval." },
  { value: "distributor", label: "Distributor", blurb: "Submits an application for staff review — an account is created only after approval." },
  { value: "employee", label: "Employee", blurb: "Submits an employment application for review — an account is created only after approval, and never with owner-level access from this form." },
];

/**
 * Single entry point for all self-service account creation, linked
 * prominently from the Login page. The role picked determines what
 * happens on submit:
 *  - Farmer: signup -> OTP verification -> a real User row is created with
 *    a hashed password (Argon2, server-side) the moment the code is
 *    verified. No account exists before that (see POST /api/v1/auth/signup
 *    and POST /api/v1/auth/verify-otp).
 *  - Dealer / Distributor / Employee: per the master spec's verification
 *    workflow, these roles do NOT get a login at signup time. The form
 *    submits a DealerApplication/DistributorApplication/StaffApplication
 *    for staff review; a User row (and hashed password) is only created
 *    by an owner/admin on approval - and for Employee specifically, the
 *    reviewer chooses the actual role granted (never owner-level from a
 *    public form) rather than trusting the applicant's requested position
 *    (see Staff -> Dealer/Distributor/Staff applications).
 */
export function Signup() {
  const [role, setRole] = useState<Role>("farmer");
  return (
    <div className="container page-section" style={{ maxWidth: 480 }}>
      <h1>Create an account</h1>
      <div className="panel">
        <div className="field">
          <label htmlFor="signup-role">I am a</label>
          <select id="signup-role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
          <p className="hint">{ROLES.find((r) => r.value === role)?.blurb}</p>
        </div>
        {role === "farmer" && <FarmerSignupForm />}
        {role === "dealer" && <DealerSignupForm />}
        {role === "distributor" && <DistributorSignupForm />}
        {role === "employee" && <EmployeeSignupForm />}
        <p className="small" style={{ marginTop: 16 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}

interface FarmerDetailsForm {
  full_name: string; email: string; phone: string; password: string;
}

const initialFarmerDetails: FarmerDetailsForm = { full_name: "", email: "", phone: "", password: "" };

function FarmerSignupForm() {
  const [step, setStep] = useState<"details" | "otp">("details");
  const [details, setDetails] = useState<FarmerDetailsForm>(initialFarmerDetails);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState<boolean | null>(null);
  const navigate = useNavigate();
  const { refresh } = useAuth();

  const requestOtp = useMutation({
    mutationFn: () => api.post<{ ok: boolean; message: string; email_sent: boolean; dev_otp_code?: string }>("/auth/signup", details),
    onSuccess: (r) => {
      setError(null);
      setEmailSent(r.email_sent);
      setDevOtp(r.dev_otp_code || null);
      setStep("otp");
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const verifyOtp = useMutation({
    mutationFn: () => api.post("/auth/verify-otp", { email: details.email, code }),
    onSuccess: async () => {
      setError(null);
      await refresh();
      navigate("/farmer");
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Incorrect or expired verification code."),
  });

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}
      {step === "details" && (
        <form onSubmit={(e) => { e.preventDefault(); requestOtp.mutate(); }}>
          <div className="field"><label htmlFor="full_name">Full name</label>
            <input type="text" id="full_name" required value={details.full_name} onChange={(e) => setDetails({ ...details, full_name: e.target.value })} /></div>
          <div className="field"><label htmlFor="email">Email</label>
            <input id="email" type="email" required value={details.email} onChange={(e) => setDetails({ ...details, email: e.target.value })} /></div>
          <div className="field"><label htmlFor="phone">Phone (10-digit mobile)</label>
            <input type="text" id="phone" required value={details.phone} onChange={(e) => setDetails({ ...details, phone: e.target.value })} /></div>
          <div className="field"><label htmlFor="password">Password</label>
            <PasswordInput id="password" required autoComplete="new-password" value={details.password} onChange={(v) => setDetails({ ...details, password: v })} />
            <p className="hint">At least 10 characters, with uppercase, lowercase, and a digit.</p></div>
          <button className="btn btn-primary" type="submit" disabled={requestOtp.isPending}>
            {requestOtp.isPending ? "Sending code..." : "Send verification code"}
          </button>
        </form>
      )}
      {step === "otp" && (
        <form onSubmit={(e) => { e.preventDefault(); verifyOtp.mutate(); }}>
          <p className="small muted">
            {emailSent
              ? <>We emailed a 6-digit verification code to <strong>{details.email}</strong>.</>
              : "Email delivery is not configured in this environment, so the code below is shown directly (this only happens in development)."}
          </p>
          {devOtp && (
            <div className="alert alert-info">Development mode: your code is <strong>{devOtp}</strong>.</div>
          )}
          <div className="field"><label htmlFor="code">Verification code</label>
            <input type="text" id="code" required inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} /></div>
          <button className="btn btn-primary" type="submit" disabled={verifyOtp.isPending}>
            {verifyOtp.isPending ? "Verifying..." : "Verify and create account"}
          </button>
          <button type="button" className="btn btn-ghost" style={{ marginLeft: 8 }} onClick={() => setStep("details")}>
            Back
          </button>
        </form>
      )}
    </>
  );
}

interface DealerSignupFormState {
  contact_person: string; business_name: string; email: string; phone: string; district: string;
  mandal: string; requested_territory: string; delivery_capability: boolean; farmer_support_interest: boolean;
  notes: string; consent_given: boolean;
}

const initialDealer: DealerSignupFormState = {
  contact_person: "", business_name: "", email: "", phone: "", district: "", mandal: "",
  requested_territory: "", delivery_capability: false, farmer_support_interest: false, notes: "", consent_given: false,
};

function DealerSignupForm() {
  const [form, setForm] = useState<DealerSignupFormState>(initialDealer);
  const [error, setError] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [docMessage, setDocMessage] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: () => api.post<{ reference_number: string; id?: string }>("/dealers/apply", form),
    onSuccess: (r) => { setReference(r.reference_number); setApplicationId(r.id || null); setError(null); },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const uploadDoc = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return uploadFile(`/media/dealer-applications/${applicationId}/documents`, fd);
    },
    onSuccess: () => setDocMessage("Document uploaded. Our team will review it with your application."),
    onError: (e: unknown) => setDocMessage(e instanceof Error ? e.message : "Upload failed."),
  });

  if (reference) {
    return (
      <div>
        <div className="alert alert-success">
          Application submitted. Your reference number is <strong>{reference}</strong>. Our team will review it and
          email you a login once approved — no password is needed yet.
        </div>
        {applicationId && (
          <div className="field">
            <label htmlFor="dealer-signup-doc">Optionally attach a business document (e.g. licence), PDF or image, up to 10MB</label>
            <input id="dealer-signup-doc" type="file" accept="image/jpeg,image/png,image/webp,application/pdf"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadDoc.mutate(f); e.target.value = ""; }} />
            {docMessage && <p className="small">{docMessage}</p>}
          </div>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="field"><label htmlFor="d-contact_person">Contact person</label>
        <input type="text" id="d-contact_person" required value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} /></div>
      <div className="field"><label htmlFor="d-business_name">Business name</label>
        <input type="text" id="d-business_name" required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} /></div>
      <div className="field"><label htmlFor="d-email">Email</label>
        <input id="d-email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
      <div className="field"><label htmlFor="d-phone">Phone (10-digit mobile)</label>
        <input type="text" id="d-phone" required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
      <div className="field"><label htmlFor="d-district">District</label>
        <input type="text" id="d-district" required value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></div>
      <div className="field"><label htmlFor="d-mandal">Mandal (optional)</label>
        <input type="text" id="d-mandal" value={form.mandal} onChange={(e) => setForm({ ...form, mandal: e.target.value })} /></div>
      <div className="field"><label htmlFor="d-territory">Requested territory (optional)</label>
        <input type="text" id="d-territory" value={form.requested_territory} onChange={(e) => setForm({ ...form, requested_territory: e.target.value })} /></div>
      <div className="field"><label htmlFor="d-notes">Additional notes (optional)</label>
        <textarea id="d-notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
      <div className="field">
        <label><input type="checkbox" checked={form.delivery_capability} onChange={(e) => setForm({ ...form, delivery_capability: e.target.checked })} /> We can offer delivery</label>
      </div>
      <div className="field">
        <label><input type="checkbox" checked={form.farmer_support_interest} onChange={(e) => setForm({ ...form, farmer_support_interest: e.target.checked })} /> Interested in receiving farmer support cases</label>
      </div>
      <div className="field">
        <label><input type="checkbox" required checked={form.consent_given} onChange={(e) => setForm({ ...form, consent_given: e.target.checked })} /> I consent to Rockstar Organics storing this information to process my application.</label>
      </div>
      <button className="btn btn-primary" type="submit" disabled={submit.isPending}>
        {submit.isPending ? "Submitting..." : "Submit application"}
      </button>
    </form>
  );
}

interface DistributorSignupFormState {
  contact_person: string; business_name: string; email: string; phone: string; territory: string;
  years_in_business: string; warehouse_capacity_notes: string; notes: string; consent_given: boolean;
}

const initialDistributor: DistributorSignupFormState = {
  contact_person: "", business_name: "", email: "", phone: "", territory: "",
  years_in_business: "", warehouse_capacity_notes: "", notes: "", consent_given: false,
};

function DistributorSignupForm() {
  const [form, setForm] = useState<DistributorSignupFormState>(initialDistributor);
  const [error, setError] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: () =>
      api.post<{ reference_number: string }>("/distributors/apply", {
        ...form,
        years_in_business: form.years_in_business ? Number(form.years_in_business) : undefined,
      }),
    onSuccess: (r) => { setReference(r.reference_number); setError(null); },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  if (reference) {
    return (
      <div className="alert alert-success">
        Application submitted. Your reference number is <strong>{reference}</strong>. Our team will review it and
        email you a login once approved — no password is needed yet.
      </div>
    );
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="field"><label htmlFor="dist-contact_person">Contact person</label>
        <input type="text" id="dist-contact_person" required value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} /></div>
      <div className="field"><label htmlFor="dist-business_name">Business name</label>
        <input type="text" id="dist-business_name" required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} /></div>
      <div className="field"><label htmlFor="dist-email">Email</label>
        <input id="dist-email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
      <div className="field"><label htmlFor="dist-phone">Phone (10-digit mobile)</label>
        <input type="text" id="dist-phone" required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
      <div className="field"><label htmlFor="dist-territory">Requested territory</label>
        <input type="text" id="dist-territory" required value={form.territory} onChange={(e) => setForm({ ...form, territory: e.target.value })} /></div>
      <div className="field"><label htmlFor="dist-years">Years in business (optional)</label>
        <input id="dist-years" type="number" min="0" value={form.years_in_business} onChange={(e) => setForm({ ...form, years_in_business: e.target.value })} /></div>
      <div className="field"><label htmlFor="dist-warehouse">Warehouse capacity notes (optional)</label>
        <textarea id="dist-warehouse" value={form.warehouse_capacity_notes} onChange={(e) => setForm({ ...form, warehouse_capacity_notes: e.target.value })} /></div>
      <div className="field"><label htmlFor="dist-notes">Additional notes (optional)</label>
        <textarea id="dist-notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
      <div className="field">
        <label><input type="checkbox" required checked={form.consent_given} onChange={(e) => setForm({ ...form, consent_given: e.target.checked })} /> I consent to Rockstar Organics storing this information to process my application.</label>
      </div>
      <button className="btn btn-primary" type="submit" disabled={submit.isPending}>
        {submit.isPending ? "Submitting..." : "Submit application"}
      </button>
    </form>
  );
}

interface EmployeeSignupFormState {
  full_name: string; email: string; phone: string; position_applied_for: string; notes: string; consent_given: boolean;
}

const initialEmployee: EmployeeSignupFormState = {
  full_name: "", email: "", phone: "", position_applied_for: "field_officer", notes: "", consent_given: false,
};

const EMPLOYEE_POSITIONS = [
  { value: "field_officer", label: "Field Officer" },
  { value: "sales_manager", label: "Sales Manager" },
  { value: "content_manager", label: "Content Manager" },
];

function EmployeeSignupForm() {
  const [form, setForm] = useState<EmployeeSignupFormState>(initialEmployee);
  const [error, setError] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: () => api.post<{ reference_number: string }>("/staff-applications", form),
    onSuccess: (r) => { setReference(r.reference_number); setError(null); },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  if (reference) {
    return (
      <div className="alert alert-success">
        Application submitted. Your reference number is <strong>{reference}</strong>. Our team will review it, and
        an administrator will provide your login only if it is approved — no password is needed yet, and this form
        never grants access on its own.
      </div>
    );
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="field"><label htmlFor="emp-full_name">Full name</label>
        <input type="text" id="emp-full_name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
      <div className="field"><label htmlFor="emp-email">Email</label>
        <input id="emp-email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
      <div className="field"><label htmlFor="emp-phone">Phone (10-digit mobile)</label>
        <input type="text" id="emp-phone" required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
      <div className="field"><label htmlFor="emp-position">Position applying for</label>
        <select id="emp-position" value={form.position_applied_for} onChange={(e) => setForm({ ...form, position_applied_for: e.target.value })}>
          {EMPLOYEE_POSITIONS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
      </div>
      <div className="field"><label htmlFor="emp-notes">Additional notes (optional)</label>
        <textarea id="emp-notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
      <div className="field">
        <label><input type="checkbox" required checked={form.consent_given} onChange={(e) => setForm({ ...form, consent_given: e.target.checked })} /> I consent to Rockstar Organics storing this information to process my application.</label>
      </div>
      <button className="btn btn-primary" type="submit" disabled={submit.isPending}>
        {submit.isPending ? "Submitting..." : "Submit application"}
      </button>
    </form>
  );
}
