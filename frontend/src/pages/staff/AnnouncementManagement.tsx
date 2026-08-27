import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface Row { id: string; title: string; slug: string; status: string; announcement_type: string; }

const TRANSITIONS: Record<string, string[]> = {
  draft: ["in_review", "archived"], in_review: ["published", "draft"], published: ["archived"], archived: ["draft"],
};

export function AnnouncementManagement() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", slug: "", summary: "", body: "", announcement_type: "general" });

  const { data, isLoading } = useQuery({ queryKey: ["admin-announcements"], queryFn: () => api.get<Row[]>("/announcements") });

  const create = useMutation({
    mutationFn: () => api.post("/announcements", form),
    onSuccess: () => {
      setShowForm(false);
      setForm({ title: "", slug: "", summary: "", body: "", announcement_type: "general" });
      qc.invalidateQueries({ queryKey: ["admin-announcements"] });
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const transition = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/announcements/${id}/transition/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-announcements"] }),
  });

  return (
    <div>
      <div className="section-heading">
        <h2>Announcements</h2>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "New announcement"}</button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {showForm && (
        <div className="panel">
          <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
            <div className="grid cols-2">
              <div className="field"><label htmlFor="a-title">Title</label><input id="a-title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
              <div className="field"><label htmlFor="a-slug">Slug</label><input id="a-slug" required value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} /></div>
            </div>
            <div className="field"><label htmlFor="a-summary">Summary</label><input id="a-summary" value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} /></div>
            <div className="field"><label htmlFor="a-body">Body</label><textarea id="a-body" required value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></div>
            <button className="btn btn-primary" type="submit" disabled={create.isPending}>Save draft</button>
          </form>
        </div>
      )}
      {isLoading && <div className="loading-state">Loading...</div>}
      {data && data.length === 0 && <EmptyState title="No announcements yet." />}
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
    </div>
  );
}
