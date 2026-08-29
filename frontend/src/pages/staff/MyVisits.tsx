import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface VisitOut {
  id: string; reference_number: string; status: string; purpose: string | null;
  scheduled_start: string | null; scheduled_end: string | null; internal_instructions: string | null;
  farmer_instructions: string | null; follow_up_required: boolean;
  case_reference: string | null; case_title: string | null; farmer_name: string | null;
}

export function MyVisits() {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["my-assigned-visits"], queryFn: () => api.get<VisitOut[]>("/visits/assigned-to-me") });

  const complete = useMutation({
    mutationFn: ({ id, summary, followUp }: { id: string; summary: string; followUp: boolean }) =>
      api.post(`/visits/${id}/complete`, { visit_summary: summary, follow_up_required: followUp }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-assigned-visits"] }),
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const handleComplete = (visitId: string) => {
    const summary = window.prompt("Visit summary (what did you find/do on this visit)?");
    if (!summary || !summary.trim()) return;
    const followUp = window.confirm("Does this visit need a follow-up task created?");
    complete.mutate({ id: visitId, summary: summary.trim(), followUp });
  };

  return (
    <div>
      <h2>My assigned visits</h2>
      <p className="muted">Field visits scheduled to you. Only you can see this list - it does not include other officers' visits.</p>
      {error && <div className="alert alert-error">{error}</div>}
      {isLoading && <div className="loading-state">Loading your visits...</div>}
      {data && data.length === 0 && <EmptyState title="No visits are currently assigned to you." />}
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Reference</th><th>Case</th><th>Farmer</th><th>Scheduled</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {data?.map((v) => (
              <tr key={v.id}>
                <td>{v.reference_number}</td>
                <td>{v.case_reference}{v.case_title ? ` — ${v.case_title}` : ""}</td>
                <td>{v.farmer_name || "—"}</td>
                <td>
                  {v.scheduled_start
                    ? `${new Date(v.scheduled_start).toLocaleString()} – ${v.scheduled_end ? new Date(v.scheduled_end).toLocaleTimeString() : ""}`
                    : "Not yet scheduled"}
                </td>
                <td><StatusBadge status={v.status} /></td>
                <td>
                  {v.status === "scheduled" && (
                    <button className="btn btn-primary btn-sm" onClick={() => handleComplete(v.id)}>Mark complete</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
