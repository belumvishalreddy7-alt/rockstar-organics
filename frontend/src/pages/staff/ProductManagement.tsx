import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, mediaUrl, uploadFile } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface ProductRow {
  id: string; sku: string; name: string; status: string; slug: string;
  category_id: string | null; short_description: string | null; full_description: string | null;
  benefits: string | null; recommended_crops: string | null; application_method: string | null;
  dosage_value: string | null; dosage_unit: string | null; manufacturing_date: string | null;
  expiry_date: string | null; precautions: string | null;
  active_ingredients: string | null; nutrient_content: string | null; concentration: string | null;
  formulation: string | null; grade: string | null; physical_form: string | null; technical_specifications: string | null;
  images: { id: string; file_path: string; alt_text: string | null }[];
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

function ProductDetailPanel({ product, onRemoveImage }: { product: ProductRow; onRemoveImage: (id: string) => void }) {
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
    </div>
  );
}
