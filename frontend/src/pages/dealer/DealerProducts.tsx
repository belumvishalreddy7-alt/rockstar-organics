import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, uploadFile } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface ProductRow {
  id: string; sku: string; name: string; status: string; slug: string;
  images: { id: string; file_path: string; alt_text: string | null }[];
}

const EMPTY_FORM = { sku: "", name: "", slug: "", short_description: "", full_description: "", precautions: "" };

export function DealerProducts() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);

  // The backend automatically scopes this to the logged-in dealer's own
  // listings only - there is no way to see or edit another dealer's drafts.
  const { data, isLoading } = useQuery({
    queryKey: ["dealer-products"],
    queryFn: () => api.get<{ items: ProductRow[] }>("/products"),
  });

  const createProduct = useMutation({
    mutationFn: () => api.post("/products", form),
    onSuccess: () => {
      setShowForm(false);
      setForm(EMPTY_FORM);
      setError(null);
      qc.invalidateQueries({ queryKey: ["dealer-products"] });
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const submitForReview = useMutation({
    mutationFn: (id: string) => api.post(`/products/${id}/transition/in_review`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dealer-products"] }),
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Could not submit for review."),
  });

  const uploadImage = useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const altText = window.prompt("Describe this image (required for accessibility)") || "";
      if (!altText.trim()) throw new Error("An image description is required.");
      const formData = new FormData();
      formData.append("file", file);
      return uploadFile(`/media/products/${id}/images?alt_text=${encodeURIComponent(altText)}`, formData);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dealer-products"] }),
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Image upload failed."),
  });

  return (
    <div>
      <div className="section-heading">
        <h2>My product listings</h2>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "Submit a new product"}
        </button>
      </div>
      <p className="muted">
        List a product with photos, a description, and usage details. Our team reviews every submission before it
        appears on the public catalogue.
      </p>
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
            <div className="field"><label htmlFor="full_description">Full description</label><textarea id="full_description" required value={form.full_description} onChange={(e) => setForm({ ...form, full_description: e.target.value })} /></div>
            <div className="field"><label htmlFor="precautions">Precautions</label><textarea id="precautions" required value={form.precautions} onChange={(e) => setForm({ ...form, precautions: e.target.value })} /></div>
            <button className="btn btn-primary" type="submit" disabled={createProduct.isPending}>Save as draft</button>
          </form>
        </div>
      )}

      {isLoading && <div className="loading-state">Loading your listings...</div>}
      {data && data.items.length === 0 && <EmptyState title="You haven't submitted any product listings yet." />}
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>SKU</th><th>Name</th><th>Status</th><th>Images</th><th>Actions</th></tr></thead>
          <tbody>
            {data?.items.map((p) => (
              <tr key={p.id}>
                <td>{p.sku}</td><td>{p.name}</td><td><StatusBadge status={p.status} /></td>
                <td>{p.images.length}</td>
                <td className="inline">
                  {p.status === "draft" && (
                    <>
                      <label className="btn btn-ghost btn-sm" style={{ cursor: "pointer" }}>
                        Upload image
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          style={{ display: "none" }}
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) uploadImage.mutate({ id: p.id, file });
                            e.target.value = "";
                          }}
                        />
                      </label>
                      <button className="btn btn-ghost btn-sm" onClick={() => submitForReview.mutate(p.id)}>
                        Submit for review
                      </button>
                    </>
                  )}
                  {p.status !== "draft" && <span className="muted">Awaiting/handled by staff</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
