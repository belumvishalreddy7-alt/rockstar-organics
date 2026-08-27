import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface Row { id: string; title: string; slug: string; status: string; }

const TRANSITIONS: Record<string, string[]> = {
  draft: ["in_review", "archived"], in_review: ["approved", "rejected", "draft"], approved: ["published", "draft"],
  published: ["archived"], archived: ["draft"], rejected: ["draft"],
};

export function KnowledgeManagement() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", slug: "", summary: "", body: "", topic: "", crops: "", region: "" });

  const { data, isLoading } = useQuery({ queryKey: ["admin-knowledge"], queryFn: () => api.get<Row[]>("/knowledge") });

  const create = useMutation({
    mutationFn: () => api.post("/knowledge", form),
    onSuccess: () => {
      setShowForm(false);
      setForm({ title: "", slug: "", summary: "", body: "", topic: "", crops: "", region: "" });
      qc.invalidateQueries({ queryKey: ["admin-knowledge"] });
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const transition = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/knowledge/${id}/transition/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-knowledge"] }),
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Transition failed."),
  });

  return (
    <div>
      <div className="section-heading">
        <h2>Crop knowledge articles</h2>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "New article"}</button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {showForm && (
        <div className="panel">
          <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
            <div className="grid cols-2">
              <div className="field"><label htmlFor="k-title">Title</label><input type="text" id="k-title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
              <div className="field"><label htmlFor="k-slug">Slug</label><input type="text" id="k-slug" required value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} /></div>
              <div className="field"><label htmlFor="k-topic">Topic</label><input type="text" id="k-topic" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} /></div>
              <div className="field"><label htmlFor="k-crops">Crops</label><input type="text" id="k-crops" value={form.crops} onChange={(e) => setForm({ ...form, crops: e.target.value })} /></div>
            </div>
            <div className="field"><label htmlFor="k-summary">Summary</label><input type="text" id="k-summary" value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} /></div>
            <div className="field"><label htmlFor="k-body">Body</label><textarea id="k-body" required value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></div>
            <button className="btn btn-primary" type="submit" disabled={create.isPending}>Save draft</button>
          </form>
        </div>
      )}
      {isLoading && <div className="loading-state">Loading...</div>}
      {data && data.length === 0 && <EmptyState title="No knowledge articles yet." />}
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Title</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {data?.map((a) => (
              <tr key={a.id}>
                <td>{a.title}</td><td><StatusBadge status={a.status} /></td>
                <td className="inline">
                  {(TRANSITIONS[a.status] || []).map((next) => (
                    <button key={next} className="btn btn-ghost btn-sm" onClick={() => transition.mutate({ id: a.id, status: next })}>{next.replace("_", " ")}</button>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted">Publication requires an approval step (In Review → Approved → Published) — this is enforced by the backend, not just the UI.</p>
    </div>
  );
}
