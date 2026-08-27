import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "../../api/client";

interface FormState {
  contact_person: string; business_name: string; email: string; phone: string; territory: string;
  years_in_business: string; warehouse_capacity_notes: string; notes: string; consent_given: boolean;
}

const initial: FormState = {
  contact_person: "", business_name: "", email: "", phone: "", territory: "",
  years_in_business: "", warehouse_capacity_notes: "", notes: "", consent_given: false,
};

export function Distributors() {
  const [form, setForm] = useState<FormState>(initial);
  const [error, setError] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: () =>
      api.post<{ reference_number: string; duplicate_warning: boolean }>("/distributors/apply", {
        ...form,
        years_in_business: form.years_in_business ? Number(form.years_in_business) : undefined,
      }),
    onSuccess: (r) => {
      setReference(r.reference_number);
      setError(null);
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  return (
    <div className="container page-section">
      <h1>Distributors</h1>
      <div className="grid cols-2">
        <div className="panel">
          <h2>Programme overview</h2>
          <p>
            Rockstar Organics works with territory-level distributors to move product from manufacturing/
            warehousing into the dealer network across Telangana.
          </p>
          <h3>Workflow</h3>
          <p>Registration &rarr; Verification &rarr; Approval &rarr; Activation.</p>
          <h3>Once activated</h3>
          <p className="small muted">
            An approved distributor gets a dedicated Distributor Login with a dashboard covering profile,
            territory information, stock, dealer relationships, enquiries, documents and account settings.
          </p>
        </div>
        <div className="panel">
          <h2>Apply</h2>
          {reference ? (
            <div className="alert alert-success">
              Application submitted. Your reference number is <strong>{reference}</strong>. Keep this for your
              records.
            </div>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="field"><label htmlFor="contact_person">Contact person</label>
                <input type="text" id="contact_person" required value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} /></div>
              <div className="field"><label htmlFor="business_name">Business name</label>
                <input type="text" id="business_name" required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} /></div>
              <div className="field"><label htmlFor="email">Email</label>
                <input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              <div className="field"><label htmlFor="phone">Phone (10-digit mobile)</label>
                <input type="text" id="phone" required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
              <div className="field"><label htmlFor="territory">Requested territory</label>
                <input type="text" id="territory" required value={form.territory} onChange={(e) => setForm({ ...form, territory: e.target.value })} /></div>
              <div className="field"><label htmlFor="years_in_business">Years in business (optional)</label>
                <input id="years_in_business" type="number" min="0" value={form.years_in_business} onChange={(e) => setForm({ ...form, years_in_business: e.target.value })} /></div>
              <div className="field"><label htmlFor="warehouse_capacity_notes">Warehouse capacity notes (optional)</label>
                <textarea id="warehouse_capacity_notes" value={form.warehouse_capacity_notes} onChange={(e) => setForm({ ...form, warehouse_capacity_notes: e.target.value })} /></div>
              <div className="field"><label htmlFor="notes">Additional notes (optional)</label>
                <textarea id="notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
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
