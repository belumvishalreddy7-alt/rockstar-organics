import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../../api/client";
import { LocationMap } from "../../components/LocationMap";

export function About() {
  const settings = useQuery({ queryKey: ["public-settings"], queryFn: () => api.get<Record<string, string | null>>("/settings/public") });
  const pending = "Information pending verification.";

  return (
    <div className="container page-section">
      <h1>About Rockstar Organics</h1>
      <div className="panel">
        <p>
          Rockstar Organics is an agricultural enterprise rooted in Telangana, India, serving the farming
          community across Ranga Reddy district and beyond. The company connects farmers, dealers, distributors,
          field officers and administrators through a unified digital platform designed to make agricultural
          inputs, knowledge and support accessible and transparent.
        </p>
        <p>
          Farmers can register, browse verified products, raise support cases and receive field visits from
          trained officers. Dealers can apply through a structured approval workflow, manage real-time stock
          availability and respond to farmer enquiries. Distributors can participate through a dedicated workflow
          covering registration, verification, approval, profile management, stock and permitted business
          operations.
        </p>
        <p>
          Every product in the catalogue moves through a controlled lifecycle: Draft &rarr; Review &rarr; Approval
          &rarr; Publication. Composition details, claims, dosage, precautions and label documents are verified
          before anything reaches the public catalogue.
        </p>
      </div>

      <div className="grid cols-2" style={{ marginTop: 24 }}>
        <div className="panel">
          <h2>Company information</h2>
          <p className="small muted">Legal name: {settings.data?.company_name || pending}</p>
          <p className="small muted">Address: {settings.data?.company_address || pending}</p>
          <p className="small muted">Registration details: {settings.data?.registration_details || pending}</p>
          <p className="small muted">Service area: {settings.data?.service_areas || pending}</p>
          <p className="small muted">
            Certifications: {settings.data?.certifications || pending}
          </p>
        </div>
        <div className="panel">
          <h2>Leadership</h2>
          <p className="small muted">Rockstar Organics leadership information will be published only after verification.</p>
          <p className="small muted">{pending}</p>
        </div>
      </div>

      <div className="grid cols-2" style={{ marginTop: 24 }}>
        <div className="panel">
          <h2>Manufacturing</h2>
          <p className="small muted">{pending}</p>
        </div>
        <div className="panel">
          <h2>Research</h2>
          <p className="small muted">{pending}</p>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 24 }}>
        <div className="section-heading">
          <h2>Official documents &amp; certificates</h2>
          <a href="/certificates">View all</a>
        </div>
        <p className="small muted">
          Company certificates and official documents are published here only after verification. See the
          <a href="/certificates"> certificates &amp; documents</a> page.
        </p>
      </div>
    </div>
  );
}

const ENQUIRY_TYPES: { value: string; label: string }[] = [
  { value: "general", label: "General" },
  { value: "product", label: "Product" },
  { value: "dealer", label: "Dealer" },
  { value: "bulk_purchase", label: "Bulk purchase" },
  { value: "business_partnership", label: "Business partnership" },
  { value: "website_issue", label: "Website issue" },
  { value: "privacy_request", label: "Privacy request" },
];

interface EnquiryForm {
  enquiry_type: string; name: string; email: string; phone: string; district: string; message: string; consent_given: boolean;
}

const initialEnquiry: EnquiryForm = {
  enquiry_type: "general", name: "", email: "", phone: "", district: "", message: "", consent_given: false,
};

export function Contact() {
  const [form, setForm] = useState<EnquiryForm>(initialEnquiry);
  const [error, setError] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: () => api.post<{ reference_number: string }>("/enquiries", form),
    onSuccess: (r) => {
      setReference(r.reference_number);
      setError(null);
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  return (
    <div className="container page-section">
      <h1>Connect with Rockstar Organics</h1>
      <p className="muted">
        Have an enquiry about Rockstar Organics, products, dealer network, distributor network or the platform?
      </p>
      <div className="grid cols-2">
        <div className="panel">
          <h2>General enquiry</h2>
          <p className="small muted">Information pending verification.</p>
          <h2>Product enquiry</h2>
          <p className="small muted">Submit a product-related enquiry through the form.</p>
          <h2>Dealer enquiry</h2>
          <p className="small muted">Apply through the <a href="/dealer-programme">dealer registration workflow</a>.</p>
          <h2>Distributor enquiry</h2>
          <p className="small muted">Use the <a href="/distributors">distributor registration workflow</a>.</p>
          <h2>Farmer platform support</h2>
          <p className="small muted">Authenticated farmers can create support cases through the farmer portal.</p>
          <h2>Service region</h2>
          <p className="small muted">A precise address is pending verification. The map below marks our confirmed service region.</p>
          <LocationMap
            locations={[]}
            fallbackQuery="Ranga Reddy district, Telangana, India"
            fallbackLabel="Rockstar Organics service region"
            height={220}
          />
        </div>
        <div className="panel">
          <h2>Send an enquiry</h2>
          {reference ? (
            <div className="alert alert-success">
              Enquiry submitted. Your reference number is <strong>{reference}</strong>.
            </div>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="field">
                <label htmlFor="enquiry_type">Enquiry type</label>
                <select id="enquiry_type" value={form.enquiry_type} onChange={(e) => setForm({ ...form, enquiry_type: e.target.value })}>
                  {ENQUIRY_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div className="field"><label htmlFor="name">Your name</label>
                <input type="text" id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div className="field"><label htmlFor="email">Email (optional)</label>
                <input id="email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              <div className="field"><label htmlFor="phone">Phone (optional)</label>
                <input type="text" id="phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
              <div className="field"><label htmlFor="district">District (optional)</label>
                <input type="text" id="district" value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></div>
              <div className="field"><label htmlFor="message">Message</label>
                <textarea id="message" required value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} /></div>
              <div className="field">
                <label><input type="checkbox" required checked={form.consent_given} onChange={(e) => setForm({ ...form, consent_given: e.target.checked })} /> I consent to Rockstar Organics storing this information to respond to my enquiry.</label>
              </div>
              <button className="btn btn-primary" type="submit" disabled={submit.isPending}>
                {submit.isPending ? "Submitting..." : "Submit enquiry"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function LegalPage({ title, body }: { title: string; body: string }) {
  return (
    <div className="container page-section">
      <h1>{title}</h1>
      <div className="panel">
        <div className="alert alert-info">This starter text requires professional legal review before production use.</div>
        <p>{body}</p>
      </div>
    </div>
  );
}

export function PrivacyPolicy() {
  return <LegalPage title="Privacy Policy" body="Rockstar Organics collects the information you provide through registration, support requests, enquiries, and dealer applications, and uses it to operate the platform described on this site." />;
}
export function Terms() {
  return <LegalPage title="Terms" body="Use of this site and its farmer, dealer, and staff portals is subject to these terms, which are pending full legal review." />;
}
export function Disclaimer() {
  return <LegalPage title="Disclaimer" body="Product information and crop knowledge content on this site is reviewed by staff but does not replace a site visit, professional agronomic advice, or label instructions." />;
}
export function CookieNotice() {
  return <LegalPage title="Cookie Notice" body="This site uses a strictly necessary session cookie to keep you signed in. No advertising or tracking cookies are used." />;
}

export function NotFound() {
  return (
    <div className="container page-section">
      <h1>Page not found</h1>
      <p className="muted">The page you're looking for doesn't exist or may have moved.</p>
      <a className="btn btn-secondary" href="/">Return home</a>
    </div>
  );
}
export function Forbidden() {
  return (
    <div className="container page-section">
      <h1>Access denied</h1>
      <p className="muted">You do not have permission to view this page.</p>
      <a className="btn btn-secondary" href="/">Return home</a>
    </div>
  );
}
export function ServerError() {
  return (
    <div className="container page-section">
      <h1>Something went wrong</h1>
      <p className="muted">An unexpected error occurred. Please try again, or contact support if this continues.</p>
    </div>
  );
}
