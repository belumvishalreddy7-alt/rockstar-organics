import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, uploadFile } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface PackSize { id: string; quantity: string; unit: string; packaging_type: string | null; sku: string | null; availability_status: string; }
interface Crop { id: string; crop_name: string; crop_category: string | null; target_use: string | null; application_stage: string | null; }
interface Claim { id: string; claim_text: string; category: string; source_evidence: string | null; verification_status: string; }
interface Certification { id: string; name: string; issuing_organization: string | null; certificate_number: string | null; verification_status: string; }
interface ProductDocument { id: string; document_type: string; title: string; verification_status: string; }

interface ProductRow {
  id: string; sku: string; name: string; status: string; slug: string;
  images: { id: string; file_path: string; alt_text: string | null }[];
  pack_size_records: PackSize[]; crops: Crop[]; claims: Claim[];
  certifications: Certification[]; documents: ProductDocument[];
}

// Every (from, to) pair the backend allows, purely for building the button
// list per row - the backend re-checks role authorization independently,
// so a button appearing here is not itself a security boundary.
const TRANSITIONS: Record<string, string[]> = {
  draft: ["pending_verification", "in_review", "archived"],
  pending_verification: ["in_review", "revision_required", "draft"],
  in_review: ["approved", "rejected", "revision_required", "draft"],
  revision_required: ["draft", "pending_verification"],
  approved: ["published", "draft"],
  published: ["unpublished", "archived"],
  unpublished: ["published", "archived"],
  archived: ["draft"],
  rejected: ["draft"],
};

const STATUS_VALUES = ["draft", "pending_verification", "in_review", "revision_required", "approved", "published", "unpublished", "archived", "rejected"];

const EMPTY_FORM = {
  sku: "", name: "", slug: "", short_description: "", full_description: "", precautions: "",
  active_ingredients: "", nutrient_content: "", concentration: "", formulation: "", grade: "", physical_form: "", technical_specifications: "",
};

const DOCUMENT_TYPES = ["technical_data_sheet", "specification", "safety_data_sheet", "certificate", "registration", "label", "brochure", "catalogue", "regulatory", "other"];
const CLAIM_CATEGORIES = ["benefit", "technical", "crop", "quality", "certification"];

export function ProductManagement() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [showComposition, setShowComposition] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-products", statusFilter],
    queryFn: () => api.get<{ items: ProductRow[] }>(`/products${statusFilter ? `?status=${statusFilter}` : ""}`),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-products"] });
  const onErr = (e: unknown) => setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Something went wrong.");

  const createProduct = useMutation({
    mutationFn: () => api.post("/products", form),
    onSuccess: () => { setShowForm(false); setForm(EMPTY_FORM); invalidate(); },
    onError: onErr,
  });

  const transition = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/products/${id}/transition/${status}`, {}),
    onSuccess: invalidate,
    onError: onErr,
  });

  const uploadImage = useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const altText = window.prompt("Alt text for this image (required for accessibility)") || "";
      if (!altText.trim()) throw new Error("Alt text is required.");
      const formData = new FormData();
      formData.append("file", file);
      return uploadFile(`/media/products/${id}/images?alt_text=${encodeURIComponent(altText)}`, formData);
    },
    onSuccess: invalidate,
    onError: onErr,
  });

  const addPackSize = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, string> }) => api.post(`/products/${id}/pack-sizes`, body),
    onSuccess: invalidate, onError: onErr,
  });
  const removePackSize = useMutation({
    mutationFn: ({ id, itemId }: { id: string; itemId: string }) => api.del(`/products/${id}/pack-sizes/${itemId}`),
    onSuccess: invalidate, onError: onErr,
  });

  const addCrop = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, string> }) => api.post(`/products/${id}/crops`, body),
    onSuccess: invalidate, onError: onErr,
  });
  const removeCrop = useMutation({
    mutationFn: ({ id, itemId }: { id: string; itemId: string }) => api.del(`/products/${id}/crops/${itemId}`),
    onSuccess: invalidate, onError: onErr,
  });

  const addClaim = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, string> }) => api.post(`/products/${id}/claims`, body),
    onSuccess: invalidate, onError: onErr,
  });
  const verifyClaim = useMutation({
    mutationFn: ({ id, itemId, status }: { id: string; itemId: string; status: string }) =>
      api.post(`/products/${id}/claims/${itemId}/verify`, { verification_status: status }),
    onSuccess: invalidate, onError: onErr,
  });
  const removeClaim = useMutation({
    mutationFn: ({ id, itemId }: { id: string; itemId: string }) => api.del(`/products/${id}/claims/${itemId}`),
    onSuccess: invalidate, onError: onErr,
  });

  const addCertification = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, string> }) => api.post(`/products/${id}/certifications`, body),
    onSuccess: invalidate, onError: onErr,
  });
  const verifyCertification = useMutation({
    mutationFn: ({ id, itemId, status }: { id: string; itemId: string; status: string }) =>
      api.post(`/products/${id}/certifications/${itemId}/verify`, { verification_status: status }),
    onSuccess: invalidate, onError: onErr,
  });
  const removeCertification = useMutation({
    mutationFn: ({ id, itemId }: { id: string; itemId: string }) => api.del(`/products/${id}/certifications/${itemId}`),
    onSuccess: invalidate, onError: onErr,
  });

  const uploadDocument = useMutation({
    mutationFn: async ({ id, file, documentType, title }: { id: string; file: File; documentType: string; title: string }) => {
      const formData = new FormData();
      formData.append("file", file);
      const uploaded = await uploadFile<{ id: string }>(`/media/products/${id}/documents`, formData);
      return api.post(`/products/${id}/documents`, { document_type: documentType, title, media_id: uploaded.id });
    },
    onSuccess: invalidate, onError: onErr,
  });
  const verifyDocument = useMutation({
    mutationFn: ({ id, itemId, status }: { id: string; itemId: string; status: string }) =>
      api.post(`/products/${id}/documents/${itemId}/verify`, { verification_status: status }),
    onSuccess: invalidate, onError: onErr,
  });
  const removeDocument = useMutation({
    mutationFn: ({ id, itemId }: { id: string; itemId: string }) => api.del(`/products/${id}/documents/${itemId}`),
    onSuccess: invalidate, onError: onErr,
  });

  return (
    <div>
      <div className="section-heading">
        <h2>Products</h2>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New draft product"}
        </button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      {showForm && (
        <div className="panel">
          <form onSubmit={(e) => { e.preventDefault(); createProduct.mutate(); }}>
            <div className="grid cols-2">
              <div className="field"><label htmlFor="sku">SKU</label><input type="text" id="sku" required value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} /></div>
              <div className="field"><label htmlFor="name">Name</label><input type="text" id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div className="field"><label htmlFor="slug">Slug (lowercase-hyphenated)</label><input type="text" id="slug" required value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} /></div>
              <div className="field"><label htmlFor="short_description">Short description</label><input type="text" id="short_description" value={form.short_description} onChange={(e) => setForm({ ...form, short_description: e.target.value })} /></div>
            </div>
            <div className="field"><label htmlFor="full_description">Full description</label><textarea id="full_description" value={form.full_description} onChange={(e) => setForm({ ...form, full_description: e.target.value })} /></div>
            <div className="field"><label htmlFor="precautions">Precautions</label><textarea id="precautions" value={form.precautions} onChange={(e) => setForm({ ...form, precautions: e.target.value })} /></div>

            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowComposition((s) => !s)}>
              {showComposition ? "Hide composition fields" : "Add composition / technical specifications"}
            </button>
            {showComposition && (
              <div className="grid cols-2">
                <div className="field"><label htmlFor="active_ingredients">Active ingredients</label><textarea id="active_ingredients" value={form.active_ingredients} onChange={(e) => setForm({ ...form, active_ingredients: e.target.value })} /></div>
                <div className="field"><label htmlFor="nutrient_content">Nutrient content</label><textarea id="nutrient_content" value={form.nutrient_content} onChange={(e) => setForm({ ...form, nutrient_content: e.target.value })} /></div>
                <div className="field"><label htmlFor="concentration">Concentration</label><input type="text" id="concentration" value={form.concentration} onChange={(e) => setForm({ ...form, concentration: e.target.value })} /></div>
                <div className="field"><label htmlFor="formulation">Formulation</label><input type="text" id="formulation" value={form.formulation} onChange={(e) => setForm({ ...form, formulation: e.target.value })} /></div>
                <div className="field"><label htmlFor="grade">Grade</label><input type="text" id="grade" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })} /></div>
                <div className="field"><label htmlFor="physical_form">Physical form</label><input type="text" id="physical_form" value={form.physical_form} onChange={(e) => setForm({ ...form, physical_form: e.target.value })} /></div>
                <div className="field"><label htmlFor="technical_specifications">Technical specifications</label><textarea id="technical_specifications" value={form.technical_specifications} onChange={(e) => setForm({ ...form, technical_specifications: e.target.value })} /></div>
              </div>
            )}
            <p className="muted">Leave any field blank if the information isn't verified yet - it will show as "Information pending verification" rather than being guessed.</p>
            <button className="btn btn-primary" type="submit" disabled={createProduct.isPending}>Save draft</button>
          </form>
        </div>
      )}

      <div className="field" style={{ maxWidth: 220 }}>
        <label htmlFor="status-filter">Filter by status</label>
        <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All</option>
          {STATUS_VALUES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
      </div>

      {isLoading && <div className="loading-state">Loading products...</div>}
      {data && data.items.length === 0 && <EmptyState title="No products match this filter." />}
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>SKU</th><th>Name</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {data?.items.map((p) => (
              <tr key={p.id}>
                <td>{p.sku}</td><td>{p.name}</td><td><StatusBadge status={p.status} /></td>
                <td className="inline">
                  {(TRANSITIONS[p.status] || []).map((next) => (
                    <button key={next} className="btn btn-ghost btn-sm" onClick={() => transition.mutate({ id: p.id, status: next })}>
                      {next.replace(/_/g, " ")}
                    </button>
                  ))}
                  <label className="btn btn-ghost btn-sm" style={{ cursor: "pointer" }}>
                    Upload image
                    <input
                      type="file" accept="image/jpeg,image/png,image/webp" style={{ display: "none" }}
                      onChange={(e) => { const file = e.target.files?.[0]; if (file) uploadImage.mutate({ id: p.id, file }); e.target.value = ""; }}
                    />
                  </label>
                  <button className="btn btn-ghost btn-sm" onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}>
                    {expandedId === p.id ? "Hide details" : "Manage details"}
                  </button>
                </td>
              </tr>
            ))}
            {data?.items.filter((p) => p.id === expandedId).map((p) => (
              <tr key={`${p.id}-detail`}>
                <td colSpan={4}>
                  <ProductDetailPanel
                    product={p}
                    onAddPackSize={(body) => addPackSize.mutate({ id: p.id, body })}
                    onRemovePackSize={(itemId) => removePackSize.mutate({ id: p.id, itemId })}
                    onAddCrop={(body) => addCrop.mutate({ id: p.id, body })}
                    onRemoveCrop={(itemId) => removeCrop.mutate({ id: p.id, itemId })}
                    onAddClaim={(body) => addClaim.mutate({ id: p.id, body })}
                    onVerifyClaim={(itemId, status) => verifyClaim.mutate({ id: p.id, itemId, status })}
                    onRemoveClaim={(itemId) => removeClaim.mutate({ id: p.id, itemId })}
                    onAddCertification={(body) => addCertification.mutate({ id: p.id, body })}
                    onVerifyCertification={(itemId, status) => verifyCertification.mutate({ id: p.id, itemId, status })}
                    onRemoveCertification={(itemId) => removeCertification.mutate({ id: p.id, itemId })}
                    onUploadDocument={(file, documentType, title) => uploadDocument.mutate({ id: p.id, file, documentType, title })}
                    onVerifyDocument={(itemId, status) => verifyDocument.mutate({ id: p.id, itemId, status })}
                    onRemoveDocument={(itemId) => removeDocument.mutate({ id: p.id, itemId })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProductDetailPanel({
  product, onAddPackSize, onRemovePackSize, onAddCrop, onRemoveCrop,
  onAddClaim, onVerifyClaim, onRemoveClaim,
  onAddCertification, onVerifyCertification, onRemoveCertification,
  onUploadDocument, onVerifyDocument, onRemoveDocument,
}: {
  product: ProductRow;
  onAddPackSize: (body: Record<string, string>) => void; onRemovePackSize: (id: string) => void;
  onAddCrop: (body: Record<string, string>) => void; onRemoveCrop: (id: string) => void;
  onAddClaim: (body: Record<string, string>) => void; onVerifyClaim: (id: string, status: string) => void; onRemoveClaim: (id: string) => void;
  onAddCertification: (body: Record<string, string>) => void; onVerifyCertification: (id: string, status: string) => void; onRemoveCertification: (id: string) => void;
  onUploadDocument: (file: File, documentType: string, title: string) => void; onVerifyDocument: (id: string, status: string) => void; onRemoveDocument: (id: string) => void;
}) {
  const [packSize, setPackSize] = useState({ quantity: "", unit: "", packaging_type: "" });
  const [crop, setCrop] = useState({ crop_name: "", crop_category: "", target_use: "", application_stage: "" });
  const [claim, setClaim] = useState({ claim_text: "", category: "benefit", source_evidence: "" });
  const [cert, setCert] = useState({ name: "", issuing_organization: "", certificate_number: "" });
  const [docTitle, setDocTitle] = useState("");
  const [docType, setDocType] = useState("technical_data_sheet");

  return (
    <div className="panel" style={{ background: "var(--surface-alt, #f7f7f5)" }}>
      <h3>Pack sizes</h3>
      <ul>
        {product.pack_size_records.map((ps) => (
          <li key={ps.id}>
            {ps.quantity} {ps.unit}{ps.packaging_type ? ` (${ps.packaging_type})` : ""} - {ps.availability_status}
            <button className="btn btn-ghost btn-sm" onClick={() => onRemovePackSize(ps.id)}>Remove</button>
          </li>
        ))}
        {product.pack_size_records.length === 0 && <li className="muted">None added yet.</li>}
      </ul>
      <form className="inline" onSubmit={(e) => { e.preventDefault(); if (!packSize.quantity || !packSize.unit) return; onAddPackSize(packSize); setPackSize({ quantity: "", unit: "", packaging_type: "" }); }}>
        <input placeholder="Quantity (e.g. 500)" value={packSize.quantity} onChange={(e) => setPackSize({ ...packSize, quantity: e.target.value })} style={{ width: 120 }} />
        <input placeholder="Unit (e.g. g, kg, L)" value={packSize.unit} onChange={(e) => setPackSize({ ...packSize, unit: e.target.value })} style={{ width: 100 }} />
        <input placeholder="Packaging type" value={packSize.packaging_type} onChange={(e) => setPackSize({ ...packSize, packaging_type: e.target.value })} style={{ width: 140 }} />
        <button className="btn btn-secondary btn-sm" type="submit">Add pack size</button>
      </form>

      <h3>Crop associations</h3>
      <ul>
        {product.crops.map((c) => (
          <li key={c.id}>
            {c.crop_name}{c.application_stage ? ` - ${c.application_stage}` : ""}
            <button className="btn btn-ghost btn-sm" onClick={() => onRemoveCrop(c.id)}>Remove</button>
          </li>
        ))}
        {product.crops.length === 0 && <li className="muted">None added yet.</li>}
      </ul>
      <form className="inline" onSubmit={(e) => { e.preventDefault(); if (!crop.crop_name) return; onAddCrop(crop); setCrop({ crop_name: "", crop_category: "", target_use: "", application_stage: "" }); }}>
        <input placeholder="Crop name" value={crop.crop_name} onChange={(e) => setCrop({ ...crop, crop_name: e.target.value })} style={{ width: 140 }} />
        <input placeholder="Application stage" value={crop.application_stage} onChange={(e) => setCrop({ ...crop, application_stage: e.target.value })} style={{ width: 140 }} />
        <button className="btn btn-secondary btn-sm" type="submit">Add crop</button>
      </form>

      <h3>Claims</h3>
      <ul>
        {product.claims.map((c) => (
          <li key={c.id}>
            <StatusBadge status={c.verification_status} /> {c.claim_text} ({c.category})
            {c.verification_status === "pending" && (
              <>
                <button className="btn btn-ghost btn-sm" onClick={() => onVerifyClaim(c.id, "verified")}>Verify</button>
                <button className="btn btn-ghost btn-sm" onClick={() => onVerifyClaim(c.id, "rejected")}>Reject</button>
              </>
            )}
            <button className="btn btn-ghost btn-sm" onClick={() => onRemoveClaim(c.id)}>Remove</button>
          </li>
        ))}
        {product.claims.length === 0 && <li className="muted">None added yet.</li>}
      </ul>
      <form className="inline" onSubmit={(e) => { e.preventDefault(); if (!claim.claim_text) return; onAddClaim(claim); setClaim({ claim_text: "", category: "benefit", source_evidence: "" }); }}>
        <input placeholder="Claim text" value={claim.claim_text} onChange={(e) => setClaim({ ...claim, claim_text: e.target.value })} style={{ width: 220 }} />
        <select value={claim.category} onChange={(e) => setClaim({ ...claim, category: e.target.value })}>
          {CLAIM_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input placeholder="Source / evidence" value={claim.source_evidence} onChange={(e) => setClaim({ ...claim, source_evidence: e.target.value })} style={{ width: 160 }} />
        <button className="btn btn-secondary btn-sm" type="submit">Add claim</button>
      </form>

      <h3>Certifications</h3>
      <ul>
        {product.certifications.map((c) => (
          <li key={c.id}>
            <StatusBadge status={c.verification_status} /> {c.name}{c.issuing_organization ? ` - ${c.issuing_organization}` : ""}
            {c.verification_status === "pending" && (
              <>
                <button className="btn btn-ghost btn-sm" onClick={() => onVerifyCertification(c.id, "verified")}>Verify</button>
                <button className="btn btn-ghost btn-sm" onClick={() => onVerifyCertification(c.id, "rejected")}>Reject</button>
              </>
            )}
            <button className="btn btn-ghost btn-sm" onClick={() => onRemoveCertification(c.id)}>Remove</button>
          </li>
        ))}
        {product.certifications.length === 0 && <li className="muted">None added yet.</li>}
      </ul>
      <form className="inline" onSubmit={(e) => { e.preventDefault(); if (!cert.name) return; onAddCertification(cert); setCert({ name: "", issuing_organization: "", certificate_number: "" }); }}>
        <input placeholder="Certification name" value={cert.name} onChange={(e) => setCert({ ...cert, name: e.target.value })} style={{ width: 180 }} />
        <input placeholder="Issuing organization" value={cert.issuing_organization} onChange={(e) => setCert({ ...cert, issuing_organization: e.target.value })} style={{ width: 180 }} />
        <input placeholder="Certificate number" value={cert.certificate_number} onChange={(e) => setCert({ ...cert, certificate_number: e.target.value })} style={{ width: 160 }} />
        <button className="btn btn-secondary btn-sm" type="submit">Add certification</button>
      </form>

      <h3>Documents</h3>
      <ul>
        {product.documents.map((d) => (
          <li key={d.id}>
            <StatusBadge status={d.verification_status} /> {d.title} ({d.document_type.replace(/_/g, " ")})
            {d.verification_status === "pending" && (
              <>
                <button className="btn btn-ghost btn-sm" onClick={() => onVerifyDocument(d.id, "verified")}>Verify</button>
                <button className="btn btn-ghost btn-sm" onClick={() => onVerifyDocument(d.id, "rejected")}>Reject</button>
              </>
            )}
            <button className="btn btn-ghost btn-sm" onClick={() => onRemoveDocument(d.id)}>Remove</button>
          </li>
        ))}
        {product.documents.length === 0 && <li className="muted">None uploaded yet.</li>}
      </ul>
      <div className="inline">
        <input placeholder="Document title" value={docTitle} onChange={(e) => setDocTitle(e.target.value)} style={{ width: 180 }} />
        <select value={docType} onChange={(e) => setDocType(e.target.value)}>
          {DOCUMENT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <label className="btn btn-secondary btn-sm" style={{ cursor: "pointer" }}>
          Upload document
          <input
            type="file" accept=".pdf,image/jpeg,image/png,image/webp" style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file && docTitle.trim()) { onUploadDocument(file, docType, docTitle.trim()); setDocTitle(""); }
              e.target.value = "";
            }}
          />
        </label>
        {!docTitle.trim() && <span className="muted">Enter a title first</span>}
      </div>
    </div>
  );
}
