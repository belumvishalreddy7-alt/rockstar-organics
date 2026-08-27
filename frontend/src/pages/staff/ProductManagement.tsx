import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, uploadFile } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface ProductRow { id: string; sku: string; name: string; status: string; slug: string; }

const TRANSITIONS: Record<string, string[]> = {
  draft: ["in_review", "archived"], in_review: ["approved", "rejected", "draft"], approved: ["published", "draft"],
  published: ["unpublished", "archived"], unpublished: ["published", "archived"], archived: ["draft"], rejected: ["draft"],
};

export function ProductManagement() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    sku: "", name: "", slug: "", short_description: "", full_description: "", precautions: "",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["admin-products", statusFilter],
    queryFn: () => api.get<{ items: ProductRow[] }>(`/products${statusFilter ? `?status=${statusFilter}` : ""}`),
  });

  const createProduct = useMutation({
    mutationFn: () => api.post("/products", form),
    onSuccess: () => {
      setShowForm(false);
      setForm({ sku: "", name: "", slug: "", short_description: "", full_description: "", precautions: "" });
      qc.invalidateQueries({ queryKey: ["admin-products"] });
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const transition = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/products/${id}/transition/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-products"] }),
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Transition failed."),
  });

  const uploadImage = useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const altText = window.prompt("Alt text for this image (required for accessibility)") || "";
      if (!altText.trim()) throw new Error("Alt text is required.");
      const formData = new FormData();
      formData.append("file", file);
      return uploadFile(`/media/products/${id}/images?alt_text=${encodeURIComponent(altText)}`, formData);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-products"] }),
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Upload failed."),
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
              <div className="field"><label htmlFor="sku">SKU</label><input id="sku" required value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} /></div>
              <div className="field"><label htmlFor="name">Name</label><input id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div className="field"><label htmlFor="slug">Slug (lowercase-hyphenated)</label><input id="slug" required value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} /></div>
              <div className="field"><label htmlFor="short_description">Short description</label><input id="short_description" value={form.short_description} onChange={(e) => setForm({ ...form, short_description: e.target.value })} /></div>
            </div>
            <div className="field"><label htmlFor="full_description">Full description</label><textarea id="full_description" value={form.full_description} onChange={(e) => setForm({ ...form, full_description: e.target.value })} /></div>
            <div className="field"><label htmlFor="precautions">Precautions</label><textarea id="precautions" value={form.precautions} onChange={(e) => setForm({ ...form, precautions: e.target.value })} /></div>
            <button className="btn btn-primary" type="submit" disabled={createProduct.isPending}>Save draft</button>
          </form>
        </div>
      )}

      <div className="field" style={{ maxWidth: 220 }}>
        <label htmlFor="status-filter">Filter by status</label>
        <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All</option>
          {["draft", "in_review", "approved", "published", "unpublished", "archived", "rejected"].map((s) => <option key={s} value={s}>{s}</option>)}
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
                      {next.replace("_", " ")}
                    </button>
                  ))}
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
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
