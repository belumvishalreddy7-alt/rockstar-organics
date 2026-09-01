import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { api, ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import { PhoneContact } from "../../components/PhoneContact";

interface AppRow { id: string; reference_number: string; business_name: string; district: string; phone: string | null; status: string; created_at: string; }

interface DocRow { id: string; original_filename: string; created_at: string; }

export function DealerApplications() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [credsMessage, setCredsMessage] = useState<string | null>(null);
  const [decideError, setDecideError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["dealer-applications"], queryFn: () => api.get<AppRow[]>("/dealers/applications") });
  const { data: docs } = useQuery({
    queryKey: ["dealer-app-docs", expanded],
    queryFn: () => api.get<DocRow[]>(`/media/dealer-applications/${expanded}/documents`),
    enabled: !!expanded,
  });

  const decide = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/dealers/applications/${id}/status/${status}`, {}),
    onSuccess: (r: unknown) => {
      setDecideError(null);
      const res = r as { dealer_credentials?: { email: string; temporary_password: string } };
      if (res.dealer_credentials) {
        setCredsMessage(`Dealer account created: ${res.dealer_credentials.email} / temporary password: ${res.dealer_credentials.temporary_password}`);
      }
      qc.invalidateQueries({ queryKey: ["dealer-applications"] });
    },
    // Without this, a failed Approve/Reject click (expired session, or a
    // real validation error) did nothing visible at all - no message, no
    // re-render, nothing - which is indistinguishable from a broken button.
    onError: (e: unknown) => setDecideError(e instanceof ApiError ? e.message : "Could not update this application. Please try again."),
  });

  const removeApplication = useMutation({
    mutationFn: (id: string) => api.del(`/dealers/applications/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dealer-applications"] }),
  });

  if (isLoading) return <div className="loading-state">Loading applications...</div>;
  if (!data || data.length === 0) return <EmptyState title="No dealer applications yet." />;

  return (
    <div>
      <h2>Dealer applications</h2>
      {decideError && <div className="alert alert-error">{decideError}</div>}
      {credsMessage && <div className="alert alert-success">{credsMessage}</div>}
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Reference</th><th>Business</th><th>District</th><th>Phone</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {data.map((a) => (
              <Fragment key={a.id}>
              <tr>
                <td>{a.reference_number}</td><td>{a.business_name}</td><td>{a.district}</td>
                <td><PhoneContact phone={a.phone} /></td>
                <td><StatusBadge status={a.status} /></td>
                <td className="inline">
                  {["new", "under_review", "information_required", "contacted", "on_hold"].includes(a.status) && (
                    <>
                      <button className="btn btn-primary btn-sm" onClick={() => decide.mutate({ id: a.id, status: "approved" })}>Approve</button>
                      <button className="btn btn-danger btn-sm" onClick={() => decide.mutate({ id: a.id, status: "rejected" })}>Reject</button>
                      <button className="btn btn-ghost btn-sm" onClick={() => decide.mutate({ id: a.id, status: "under_review" })}>Mark under review</button>
                    </>
                  )}
                  <button className="btn btn-ghost btn-sm" onClick={() => setExpanded(expanded === a.id ? null : a.id)}>
                    {expanded === a.id ? "Hide documents" : "View documents"}
                  </button>
                  {user?.role === "super_admin" && (
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => {
                        if (window.confirm(`Permanently delete this application from "${a.business_name}"? This cannot be undone.`)) removeApplication.mutate(a.id);
                      }}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
              {expanded === a.id && (
                <tr>
                  <td colSpan={6}>
                    <div className="panel">
                      <h4>Submitted documents</h4>
                      {docs && docs.length === 0 && <p className="small muted">No documents submitted.</p>}
                      <ul>
                        {docs?.map((d) => <li key={d.id}>{d.original_filename} — {new Date(d.created_at).toLocaleDateString()}</li>)}
                      </ul>
                    </div>
                  </td>
                </tr>
              )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
