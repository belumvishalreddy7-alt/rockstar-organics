import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface CaseRow { id: string; reference_number: string; title: string; status: string; district: string; priority: string; }
interface Match { dealer_id: string; business_name: string; score: number; reasons: string[]; }

export function CaseQueue() {
  const qc = useQueryClient();
  const [expandedCase, setExpandedCase] = useState<string | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["staff-cases"], queryFn: () => api.get<CaseRow[]>("/cases") });

  const { data: matches } = useQuery({
    queryKey: ["case-matches", expandedCase],
    queryFn: () => api.get<Match[]>(`/cases/${expandedCase}/matches`),
    enabled: !!expandedCase,
  });

  const assign = useMutation({
    mutationFn: ({ caseId, dealerId }: { caseId: string; dealerId: string }) => api.post(`/cases/${caseId}/assign`, { dealer_id: dealerId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["staff-cases"] });
      setExpandedCase(null);
    },
  });

  if (isLoading) return <div className="loading-state">Loading cases...</div>;
  if (!data || data.length === 0) return <EmptyState title="No farmer support cases yet." />;

  return (
    <div>
      <h2>Farmer support cases</h2>
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Reference</th><th>Title</th><th>District</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {data.map((c) => (
              <>
                <tr key={c.id}>
                  <td>{c.reference_number}</td><td>{c.title}</td><td>{c.district}</td><td>{c.priority}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td>
                    <button className="btn btn-ghost btn-sm" onClick={() => setExpandedCase(expandedCase === c.id ? null : c.id)}>
                      {expandedCase === c.id ? "Hide matches" : "View dealer matches"}
                    </button>
                  </td>
                </tr>
                {expandedCase === c.id && (
                  <tr>
                    <td colSpan={6}>
                      <div className="panel">
                        <h3>Transparent dealer matches</h3>
                        {matches && matches.length === 0 && <p className="small muted">No matching dealers found for this district/mandal.</p>}
                        <ul className="stack" style={{ listStyle: "none", padding: 0 }}>
                          {matches?.map((m) => (
                            <li key={m.dealer_id} className="inline">
                              <strong>{m.business_name}</strong>
                              <span className="small muted">score {m.score} — {m.reasons.join("; ")}</span>
                              <button className="btn btn-primary btn-sm" onClick={() => assign.mutate({ caseId: c.id, dealerId: m.dealer_id })}>Assign</button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
