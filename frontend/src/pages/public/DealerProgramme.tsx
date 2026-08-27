import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError, uploadFile } from "../../api/client";

interface FormState {
  contact_person: string; business_name: string; email: string; phone: string; district: string;
  mandal: string; requested_territory: string; delivery_capability: boolean; farmer_support_interest: boolean;
  notes: string; consent_given: boolean;
}

const initial: FormState = {
  contact_person: "", business_name: "", email: "", phone: "", district: "", mandal: "",
  requested_territory: "", delivery_capability: false, farmer_support_interest: false, notes: "", consent_given: false,
};

export function DealerProgramme() {
  const [form, setForm] = useState<FormState>(initial);
  const [error, setError] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);

  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [docMessage, setDocMessage] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: () => api.post<{ reference_number: string; duplicate_warning: boolean; id?: string }>("/dealers/apply", form),
    onSuccess: (r) => {
      setReference(r.reference_number);
      setApplicationId(r.id || null);
      setError(null);
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const uploadDoc = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return uploadFile(`/media/dealer-applications/${applicationId}/documents`, formData);
    },
    onSuccess: () => setDocMessage("Document uploaded. Our team will review it with your application."),
    onError: (e: unknown) => setDocMessage(e instanceof Error ? e.message : "Upload failed."),
  });

  return (
    <div className="container page-section">
      <h1>Dealer programme</h1>
      <div className="grid cols-2">
        <div className="panel">
          <h2>Programme overview</h2>
          <p>Rockstar Organics works with local agricultural dealers to reach farmers across Hyderabad, Ranga Reddy, and nearby districts.</p>
          <h3>Eligibility</h3>
          <p>An existing or planned agricultural retail business serving one or more districts in our operating region.</p>
          <h3>Process</h3>
          <p>Submit the application below. Our sales team reviews applications and may contact you for more information before a decision.</p>
        </div>
        <div className="panel">
          <h2>Apply</h2>
          {reference ? (
            <div>
              <div className="alert alert-success">
                Application submitted. Your reference number is <strong>{reference}</strong>. Keep this for your records.
              </div>
              {applicationId && (
                <div className="field">
                  <label htmlFor="dealer-doc">Optionally attach a business document (e.g. licence), PDF or image, up to 10MB</label>
                  <input
                    id="dealer-doc"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) uploadDoc.mutate(file);
                      e.target.value = "";
                    }}
                  />
                  {docMessage && <p className="small">{docMessage}</p>}
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="field"><label htmlFor="contact_person">Contact person</label>
                <input id="contact_person" required value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} /></div>
              <div className="field"><label htmlFor="business_name">Business name</label>
                <input id="business_name" required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} /></div>
              <div className="field"><label htmlFor="email">Email</label>
                <input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              <div className="field"><label htmlFor="phone">Phone (10-digit mobile)</label>
                <input id="phone" required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
              <div className="field"><label htmlFor="district">District</label>
                <input id="district" required value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></div>
              <div className="field"><label htmlFor="mandal">Mandal (optional)</label>
                <input id="mandal" value={form.mandal} onChange={(e) => setForm({ ...form, mandal: e.target.value })} /></div>
              <div className="field"><label htmlFor="requested_territory">Requested territory (optional)</label>
                <input id="requested_territory" value={form.requested_territory} onChange={(e) => setForm({ ...form, requested_territory: e.target.value })} /></div>
              <div className="field"><label htmlFor="notes">Additional notes (optional)</label>
                <textarea id="notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
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
          )}
        </div>
      </div>
    </div>
  );
}
