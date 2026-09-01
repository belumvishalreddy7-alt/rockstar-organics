import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import { PhoneContact } from "../../components/PhoneContact";

interface AppRow { id: string; reference_number: string; business_name: string; territory: string; phone: string | null; status: string; created_at: string; }

export function DistributorApplications() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [credsMessage, setCredsMessage] = useState<string | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["distributor-applications"], queryFn: () => api.get<AppRow[]>("/distributors/applications") });

  const decide = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/distributors/applications/${id}/status/${status}`, {}),
    onSuccess: (r: unknown) => {
      const res = r as { distributor_credentials?: { email: string; temporary_password: string; email_delivery?: string } };
      if (res.distributor_credentials) {
        const c = res.distributor_credentials;
        setCredsMessage(
          `Distributor account created: ${c.email} / temporary password: ${c.temporary_password}` +
          (c.email_delivery ? ` (email not sent: ${c.email_delivery})` : " (credentials emailed to the applicant)")
        );
      }
      qc.invalidateQueries({ queryKey: ["distributor-applications"] });
    },
  });

  const removeApplication = useMutation({
    mutationFn: (id: string) => api.del(`/distributors/applications/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["distributor-applications"] }),
  });

  if (isLoading) return <div className="loading-state">Loading applications...</div>;
  if (!data || data.length === 0) return <EmptyState title="No distributor applications yet." />;

  return (
    <div>
      <h2>Distributor applications</h2>
      {credsMessage && <div className="alert alert-success">{credsMessage}</div>}
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Reference</th><th>Business</th><th>Territory</th><th>Phone</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {data.map((a) => (
              <tr key={a.id}>
                <td>{a.reference_number}</td><td>{a.business_name}</td><td>{a.territory}</td>
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
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
