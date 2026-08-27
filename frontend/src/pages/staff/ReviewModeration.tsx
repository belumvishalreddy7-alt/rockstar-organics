import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";

interface PendingReview { id: string; product_id: string; reviewer_name: string; rating: number; comment: string | null; created_at: string; }

export function ReviewModeration() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["pending-reviews"], queryFn: () => api.get<PendingReview[]>("/reviews/pending") });

  const moderate = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/reviews/${id}/moderate`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pending-reviews"] }),
  });

  if (isLoading) return <div className="loading-state">Loading pending reviews...</div>;
  if (!data || data.length === 0) return <EmptyState title="No reviews awaiting moderation." />;

  return (
    <div>
      <h2>Pending product reviews</h2>
      <div className="stack">
        {data.map((r) => (
          <div className="panel" key={r.id}>
            <p><strong>{r.reviewer_name}</strong> — {r.rating}/5</p>
            {r.comment && <p className="small">{r.comment}</p>}
            <div className="inline">
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
