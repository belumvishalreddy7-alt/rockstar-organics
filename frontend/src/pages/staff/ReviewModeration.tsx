import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface PendingReview {
  id: string; product_id: string; reviewer_name: string; rating: number; comment: string | null;
  status: string; created_at: string;
}

export function ReviewModeration() {
  const qc = useQueryClient();
  const [notes, setNotes] = useState<Record<string, string>>({});
  const { data, isLoading } = useQuery({ queryKey: ["pending-reviews"], queryFn: () => api.get<PendingReview[]>("/reviews/pending") });

  const moderate = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.post(`/reviews/${id}/moderate`, { status, moderator_notes: notes[id] || undefined }),
    onSuccess: (_data, { id }) => {
      setNotes((n) => { const next = { ...n }; delete next[id]; return next; });
      qc.invalidateQueries({ queryKey: ["pending-reviews"] });
    },
  });

  if (isLoading) return <div className="loading-state">Loading pending reviews...</div>;
  if (!data || data.length === 0) return <EmptyState title="No reviews awaiting moderation." />;

  return (
    <div>
      <h2>Farmer rating moderation</h2>
      <p className="small muted">Only approved ratings ever appear on the public product page - a moderation reason recorded here is kept as part of the review's audit history.</p>
      <div className="stack">
        {data.map((r) => (
          <div className="panel" key={r.id}>
            <div className="inline">
              <strong>{r.reviewer_name}</strong>
              <span>— {r.rating}/5</span>
              <StatusBadge status={r.status} />
              <span className="small muted">Product: {r.product_id}</span>
            </div>
            {r.comment && <p className="small">{r.comment}</p>}
            <div className="field" style={{ marginTop: 8 }}>
              <label htmlFor={`notes-${r.id}`} className="small">Moderation reason (optional)</label>
              <input
                type="text" id={`notes-${r.id}`} value={notes[r.id] || ""}
                onChange={(e) => setNotes((n) => ({ ...n, [r.id]: e.target.value }))}
              />
            </div>
            <div className="inline">
              {r.status !== "under_review" && (
                <button className="btn btn-ghost btn-sm" onClick={() => moderate.mutate({ id: r.id, status: "under_review" })}>Mark under review</button>
              )}
              <button className="btn btn-primary btn-sm" onClick={() => moderate.mutate({ id: r.id, status: "approved" })}>Approve</button>
              <button className="btn btn-danger btn-sm" onClick={() => moderate.mutate({ id: r.id, status: "rejected" })}>Reject</button>
              <button className="btn btn-ghost btn-sm" onClick={() => moderate.mutate({ id: r.id, status: "spam" })}>Mark spam</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
