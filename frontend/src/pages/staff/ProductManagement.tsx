import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, mediaUrl, uploadFile } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface PackSize { id: string; quantity: string; unit: string; packaging_type: string | null; sku: string | null; price: number | null; availability_status: string; }
interface Crop { id: string; crop_name: string; crop_category: string | null; target_use: string | null; application_stage: string | null; }
interface Claim { id: string; claim_text: string; category: string; source_evidence: string | null; verification_status: string; }
interface Certification { id: string; name: string; issuing_organization: string | null; certificate_number: string | null; verification_status: string; }
interface ProductDocument { id: string; document_type: string; title: string; verification_status: string; }

interface ProductRow {
  id: string; sku: string; name: string; status: string; slug: string;
  category_id: string | null; short_description: string | null; full_description: string | null;
  benefits: string | null; recommended_crops: string | null; application_method: string | null;
  dosage_value: string | null; dosage_unit: string | null; manufacturing_date: string | null;
  expiry_date: string | null; precautions: string | null;
  active_ingredients: string | null; nutrient_content: string | null; concentration: string | null;
  formulation: string | null; grade: string | null; physical_form: string | null; technical_specifications: string | null;
  images: { id: string; file_path: string; alt_text: string | null }[];
  pack_size_records: PackSize[]; crops: Crop[]; claims: Claim[];
  certifications: Certification[]; documents: ProductDocument[];
}

interface Category { id: string; name: string; slug: string; }

type ProductFieldValues = {
  sku: string; name: string; slug: string; category_id: string; short_description: string; full_description: string;
  precautions: string; benefits: string; recommended_crops: string; application_method: string;
  dosage_value: string; dosage_unit: string; manufacturing_date: string; expiry_date: string;
  active_ingredients: string; nutrient_content: string; concentration: string; formulation: string;
  grade: string; physical_form: string; technical_specifications: string;
};

function rowToFieldValues(p: ProductRow): ProductFieldValues {
  return {
    sku: p.sku, name: p.name, slug: p.slug, category_id: p.category_id || "",
    short_description: p.short_description || "", full_description: p.full_description || "",
    precautions: p.precautions || "", benefits: p.benefits || "", recommended_crops: p.recommended_crops || "",
    application_method: p.application_method || "", dosage_value: p.dosage_value || "", dosage_unit: p.dosage_unit || "",
    manufacturing_date: p.manufacturing_date || "", expiry_date: p.expiry_date || "",
    active_ingredients: p.active_ingredients || "", nutrient_content: p.nutrient_content || "",
    concentration: p.concentration || "", formulation: p.formulation || "", grade: p.grade || "",
    physical_form: p.physical_form || "", technical_specifications: p.technical_specifications || "",
  };
}

/** Sends every ProductUpdate field, not just the ones the caller touched -
 * PUT /products/{id} replaces the whole row (model_dump() with no
 * exclude_unset), so submitting a partial body would silently null out
 * every field this form doesn't know about. */
function ProductFields({ values, onChange, categories, onCategoryCreated }: {
  values: ProductFieldValues; onChange: (v: ProductFieldValues) => void;
  categories: Category[] | undefined; onCategoryCreated: (id: string) => void;
}) {
  const [showComposition, setShowComposition] = useState(false);
  const set = <K extends keyof ProductFieldValues>(key: K, val: ProductFieldValues[K]) => onChange({ ...values, [key]: val });

  return (
    <>
      <div className="grid cols-2">
        <div className="field"><label>SKU</label><input type="text" required value={values.sku} onChange={(e) => set("sku", e.target.value)} /></div>
        <div className="field"><label>Name</label><input type="text" required value={values.name} onChange={(e) => set("name", e.target.value)} /></div>
        <div className="field"><label>Slug (lowercase-hyphenated)</label><input type="text" required value={values.slug} onChange={(e) => set("slug", e.target.value)} /></div>
        <div className="field">
          <label>Category</label>
          <div className="inline">
            <select value={values.category_id} onChange={(e) => set("category_id", e.target.value)} style={{ flex: 1 }}>
              <option value="">Not set</option>
              {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <button
              type="button" className="btn btn-ghost btn-sm"
              onClick={async () => {
                const name = window.prompt("New category name:");
                if (!name?.trim()) return;
                const slug = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
                try {
                  const created = await api.post<Category>("/categories", { name: name.trim(), slug });
                  onCategoryCreated(created.id);
                } catch {
                  window.alert("Could not create that category - it may already exist.");
                }
              }}
            >
              + New
            </button>
          </div>
        </div>
        <div className="field"><label>Short description</label><input type="text" value={values.short_description} onChange={(e) => set("short_description", e.target.value)} /></div>
      </div>
      <div className="field"><label>Full description</label><textarea value={values.full_description} onChange={(e) => set("full_description", e.target.value)} /></div>
      <div className="field"><label>Uses / benefits</label><textarea value={values.benefits} onChange={(e) => set("benefits", e.target.value)} /></div>
      <div className="grid cols-2">
        <div className="field"><label>Recommended crops</label><input type="text" value={values.recommended_crops} onChange={(e) => set("recommended_crops", e.target.value)} /></div>
        <div className="field"><label>Application method</label><input type="text" value={values.application_method} onChange={(e) => set("application_method", e.target.value)} /></div>
        <div className="field"><label>Dosage value</label><input type="text" placeholder="e.g. 2" value={values.dosage_value} onChange={(e) => set("dosage_value", e.target.value)} /></div>
        <div className="field"><label>Dosage unit</label><input type="text" placeholder="e.g. ml/L, g/L" value={values.dosage_unit} onChange={(e) => set("dosage_unit", e.target.value)} /></div>
        <div className="field"><label>Manufacturing date</label><input type="date" value={values.manufacturing_date} onChange={(e) => set("manufacturing_date", e.target.value)} /></div>
        <div className="field"><label>Expiry date</label><input type="date" value={values.expiry_date} onChange={(e) => set("expiry_date", e.target.value)} /></div>
      </div>
      <div className="field"><label>Precautions</label><textarea value={values.precautions} onChange={(e) => set("precautions", e.target.value)} /></div>

      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowComposition((s) => !s)}>
        {showComposition ? "Hide composition fields" : "Add composition / technical specifications"}
      </button>
      {showComposition && (
        <div className="grid cols-2">
          <div className="field"><label>Active ingredients</label><textarea value={values.active_ingredients} onChange={(e) => set("active_ingredients", e.target.value)} /></div>
          <div className="field"><label>Nutrient content</label><textarea value={values.nutrient_content} onChange={(e) => set("nutrient_content", e.target.value)} /></div>
          <div className="field"><label>Concentration</label><input type="text" value={values.concentration} onChange={(e) => set("concentration", e.target.value)} /></div>
          <div className="field"><label>Formulation</label><input type="text" value={values.formulation} onChange={(e) => set("formulation", e.target.value)} /></div>
          <div className="field"><label>Grade</label><input type="text" value={values.grade} onChange={(e) => set("grade", e.target.value)} /></div>
          <div className="field"><label>Physical form</label><input type="text" value={values.physical_form} onChange={(e) => set("physical_form", e.target.value)} /></div>
          <div className="field"><label>Technical specifications</label><textarea value={values.technical_specifications} onChange={(e) => set("technical_specifications", e.target.value)} /></div>
        </div>
      )}
      <p className="muted">Leave any field blank if the information isn't verified yet - it will show as "Information pending verification" rather than being guessed.</p>
    </>
  );
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

const EMPTY_FORM: ProductFieldValues = {
  sku: "", name: "", slug: "", category_id: "", short_description: "", full_description: "", precautions: "",
  benefits: "", recommended_crops: "", application_method: "", dosage_value: "", dosage_unit: "",
  manufacturing_date: "", expiry_date: "",
  active_ingredients: "", nutrient_content: "", concentration: "", formulation: "", grade: "", physical_form: "", technical_specifications: "",
};

/** category_id/manufacturing_date/expiry_date are "" in the form state
 * (plain controlled inputs) but the backend needs null, not an empty
 * string, for an optional FK/date field - an empty string fails Pydantic's
 * date parsing outright, the same lesson as the pack-size price field. */
function fieldsToPayload(v: ProductFieldValues) {
  return {
    ...v,
    category_id: v.category_id || null,
    manufacturing_date: v.manufacturing_date || null,
    expiry_date: v.expiry_date || null,
  };
}

const DOCUMENT_TYPES = ["technical_data_sheet", "specification", "safety_data_sheet", "certificate", "registration", "label", "brochure", "catalogue", "regulatory", "other"];
const CLAIM_CATEGORIES = ["benefit", "technical", "crop", "quality", "certification"];

export function ProductManagement() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [newImage, setNewImage] = useState<File | null>(null);
  const [newImageAlt, setNewImageAlt] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-products", statusFilter],
    queryFn: () => api.get<{ items: ProductRow[] }>(`/products${statusFilter ? `?status=${statusFilter}` : ""}`),
  });
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: () => api.get<Category[]>("/categories/public") });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-products"] });
  const invalidateCategories = () => qc.invalidateQueries({ queryKey: ["categories"] });
  const onErr = (e: unknown) => setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Something went wrong.");

  const createProduct = useMutation({
    mutationFn: async () => {
      const created = await api.post<{ id: string }>("/products", fieldsToPayload(form));
      if (newImage) {
        const formData = new FormData();
        formData.append("file", newImage);
        await uploadFile(`/media/products/${created.id}/images?alt_text=${encodeURIComponent(newImageAlt)}`, formData);
      }
      return created;
    },
    onSuccess: () => { setShowForm(false); setForm(EMPTY_FORM); setNewImage(null); setNewImageAlt(""); invalidate(); },
    onError: onErr,
  });

  const transition = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/products/${id}/transition/${status}`, {}),
    onSuccess: invalidate,
    onError: onErr,
  });

  const removeProduct = useMutation({
    mutationFn: (id: string) => api.del(`/products/${id}`),
    onSuccess: invalidate,
    onError: onErr,
  });

  const updateProduct = useMutation({
    mutationFn: ({ id, values }: { id: string; values: ProductFieldValues }) => api.put(`/products/${id}`, fieldsToPayload(values)),
    onSuccess: () => { setError(null); invalidate(); },
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

  const removeImage = useMutation({
    mutationFn: ({ id, imageId }: { id: string; imageId: string }) => api.del(`/products/${id}/images/${imageId}`),
    onSuccess: invalidate, onError: onErr,
  });

  const addPackSize = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, string | number | null> }) => api.post(`/products/${id}/pack-sizes`, body),
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
        <button className="btn btn-primary btn-sm" onClick={() => {
          setShowForm((s) => !s);
          setNewImage(null); setNewImageAlt(""); setError(null);
        }}>
          {showForm ? "Cancel" : "New draft product"}
        </button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      {showForm && (
        <div className="panel">
          <form onSubmit={(e) => {
            e.preventDefault();
            if (!newImage) { setError("A product image is required to save this draft."); return; }
            if (!newImageAlt.trim()) { setError("Image alt text is required when a product image is attached."); return; }
            setError(null);
            createProduct.mutate();
          }}>
            <ProductFields values={form} onChange={setForm} categories={categories} onCategoryCreated={(id) => { setForm({ ...form, category_id: id }); invalidateCategories(); }} />

            <div className="grid cols-2">
              <div className="field">
                <label htmlFor="new-image">Product image (required)</label>
                <input id="new-image" type="file" accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => setNewImage(e.target.files?.[0] || null)} />
              </div>
              {newImage && (
                <div className="field">
                  <label htmlFor="new-image-alt">Image alt text (required for this image)</label>
                  <input id="new-image-alt" type="text" value={newImageAlt} onChange={(e) => setNewImageAlt(e.target.value)} />
                </div>
              )}
            </div>
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
                  {user?.role === "super_admin" && (
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => {
                        if (window.confirm(`Permanently delete "${p.name}" (${p.sku})? This cannot be undone.`)) removeProduct.mutate(p.id);
                      }}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {data?.items.filter((p) => p.id === expandedId).map((p) => (
              <tr key={`${p.id}-detail`}>
                <td colSpan={4}>
                  <ProductEditForm
                    key={p.id}
                    product={p}
                    categories={categories}
                    onCategoryCreated={invalidateCategories}
                    isSaving={updateProduct.isPending}
                    onSave={(values) => updateProduct.mutate({ id: p.id, values })}
                  />
                  <ProductDetailPanel
                    product={p}
                    onRemoveImage={(imageId) => removeImage.mutate({ id: p.id, imageId })}
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

function ProductEditForm({ product, categories, onCategoryCreated, onSave, isSaving }: {
  product: ProductRow; categories: Category[] | undefined; onCategoryCreated: () => void;
  onSave: (values: ProductFieldValues) => void; isSaving: boolean;
}) {
  const [values, setValues] = useState<ProductFieldValues>(() => rowToFieldValues(product));

  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <h3>Edit details</h3>
      <form onSubmit={(e) => { e.preventDefault(); onSave(values); }}>
        <ProductFields
          values={values} onChange={setValues} categories={categories}
          onCategoryCreated={(id) => { setValues({ ...values, category_id: id }); onCategoryCreated(); }}
        />
        <button className="btn btn-primary btn-sm" type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : "Save changes"}
        </button>
      </form>
    </div>
  );
}

function ProductDetailPanel({
  product, onRemoveImage, onAddPackSize, onRemovePackSize, onAddCrop, onRemoveCrop,
  onAddClaim, onVerifyClaim, onRemoveClaim,
  onAddCertification, onVerifyCertification, onRemoveCertification,
  onUploadDocument, onVerifyDocument, onRemoveDocument,
}: {
  product: ProductRow;
  onRemoveImage: (id: string) => void;
  onAddPackSize: (body: Record<string, string | number | null>) => void; onRemovePackSize: (id: string) => void;
  onAddCrop: (body: Record<string, string>) => void; onRemoveCrop: (id: string) => void;
  onAddClaim: (body: Record<string, string>) => void; onVerifyClaim: (id: string, status: string) => void; onRemoveClaim: (id: string) => void;
  onAddCertification: (body: Record<string, string>) => void; onVerifyCertification: (id: string, status: string) => void; onRemoveCertification: (id: string) => void;
  onUploadDocument: (file: File, documentType: string, title: string) => void; onVerifyDocument: (id: string, status: string) => void; onRemoveDocument: (id: string) => void;
}) {
  const [packSize, setPackSize] = useState({ quantity: "", unit: "", packaging_type: "", price: "" });
  const [crop, setCrop] = useState({ crop_name: "", crop_category: "", target_use: "", application_stage: "" });
  const [claim, setClaim] = useState({ claim_text: "", category: "benefit", source_evidence: "" });
  const [cert, setCert] = useState({ name: "", issuing_organization: "", certificate_number: "" });
  const [docTitle, setDocTitle] = useState("");
  const [docType, setDocType] = useState("technical_data_sheet");

  return (
    <div className="panel" style={{ background: "var(--surface-alt, #f7f7f5)" }}>
      <h3>Images</h3>
      {product.images.length === 0 && <p className="muted">No images uploaded yet.</p>}
      <div className="inline" style={{ flexWrap: "wrap", alignItems: "flex-start" }}>
        {product.images.map((img) => (
          <div key={img.id} style={{ width: 120 }}>
            <img
              src={mediaUrl(`/api/v1/media/public/${img.file_path.replace(/^public\//, "")}`)}
              alt={img.alt_text || ""}
              style={{ width: "100%", height: 90, objectFit: "cover", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)" }}
            />
            <p className="small muted" style={{ margin: "4px 0" }}>{img.alt_text || "No alt text"}</p>
            <button className="btn btn-danger btn-sm" onClick={() => onRemoveImage(img.id)}>Remove</button>
          </div>
        ))}
      </div>

      <h3>Pack sizes &amp; rate</h3>
      <ul>
        {product.pack_size_records.map((ps) => (
          <li key={ps.id}>
            {ps.quantity} {ps.unit}{ps.packaging_type ? ` (${ps.packaging_type})` : ""} - {ps.price != null ? `₹${ps.price.toFixed(2)}` : "rate pending"} - {ps.availability_status}
            <button className="btn btn-ghost btn-sm" onClick={() => onRemovePackSize(ps.id)}>Remove</button>
          </li>
        ))}
        {product.pack_size_records.length === 0 && <li className="muted">None added yet.</li>}
      </ul>
      <form className="inline" onSubmit={(e) => {
        e.preventDefault();
        if (!packSize.quantity || !packSize.unit) return;
        onAddPackSize({
          quantity: packSize.quantity, unit: packSize.unit, packaging_type: packSize.packaging_type || null,
          price: packSize.price ? Number(packSize.price) : null,
        });
        setPackSize({ quantity: "", unit: "", packaging_type: "", price: "" });
      }}>
        <input placeholder="Quantity (e.g. 500)" value={packSize.quantity} onChange={(e) => setPackSize({ ...packSize, quantity: e.target.value })} style={{ width: 120 }} />
        <input placeholder="Unit (e.g. ml, L, g, kg)" value={packSize.unit} onChange={(e) => setPackSize({ ...packSize, unit: e.target.value })} style={{ width: 110 }} />
        <input placeholder="Packaging type" value={packSize.packaging_type} onChange={(e) => setPackSize({ ...packSize, packaging_type: e.target.value })} style={{ width: 140 }} />
        <input type="number" min="0" step="0.01" placeholder="Rate (₹)" value={packSize.price} onChange={(e) => setPackSize({ ...packSize, price: e.target.value })} style={{ width: 110 }} />
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
