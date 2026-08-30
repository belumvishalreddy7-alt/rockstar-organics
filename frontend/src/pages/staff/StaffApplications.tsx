import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import { PhoneContact } from "../../components/PhoneContact";

const SETTINGS_MANAGER_ROLES = ["super_admin", "admin"];

interface AppRow {
  id: string; reference_number: string; full_name: string; email: string; phone: string;
  position_applied_for: string; status: string; created_at: string;
}

const GRANTABLE_ROLES = [
  { value: "field_officer", label: "Field Officer" },
  { value: "sales_manager", label: "Sales Manager" },
  { value: "content_manager", label: "Content Manager" },
  { value: "admin", label: "Manager (Admin)" },
  { value: "super_admin", label: "Owner (Super Administrator)" },
];

export function StaffApplications() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [credsMessage, setCredsMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<Record<string, string>>({});
  const enabled = !!user && SETTINGS_MANAGER_ROLES.includes(user.role);
  const { data, isLoading } = useQuery({ queryKey: ["staff-applications"], queryFn: () => api.get<AppRow[]>("/staff-applications"), enabled });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/staff-applications/${id}/status/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["staff-applications"] }),
  });

  const approve = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) => api.post<{ staff_credentials: { email: string; temporary_password: string } }>(`/staff-applications/${id}/approve`, { role }),
    onSuccess: (r) => {
      setCredsMessage(`Account created: ${r.staff_credentials.email} / temporary password: ${r.staff_credentials.temporary_password}`);
      setError(null);
      qc.invalidateQueries({ queryKey: ["staff-applications"] });
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Could not approve this application."),
  });

  if (!enabled) {
    return (
      <div>
        <h2>Staff (employment) applications</h2>
        <p className="muted">Only the owner or a manager can review employment applications.</p>
      </div>
    );
  }

  if (isLoading) return <div className="loading-state">Loading applications...</div>;
  if (!data || data.length === 0) return <EmptyState title="No employment applications yet." />;

  return (
    <div>
      <h2>Staff (employment) applications</h2>
      <p className="small muted">
        Approving grants the role you choose here - not necessarily the position the applicant requested. Only a
        Super Administrator can grant Owner (Super Administrator) access.
      </p>
      {credsMessage && <div className="alert alert-success">{credsMessage}</div>}
      {error && <div className="alert alert-error">{error}</div>}
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Reference</th><th>Name</th><th>Phone</th><th>Position requested</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {data.map((a) => (
              <tr key={a.id}>
                <td>{a.reference_number}</td>
                <td>{a.full_name}<div className="small muted">{a.email}</div></td>
                <td><PhoneContact phone={a.phone} /></td>
                <td>{a.position_applied_for.replace(/_/g, " ")}</td>
                <td><StatusBadge status={a.status} /></td>
                <td className="inline">
                  {["new", "under_review", "information_required", "contacted", "on_hold"].includes(a.status) && (
                    <>
                      <select value={selectedRole[a.id] || a.position_applied_for} onChange={(e) => setSelectedRole({ ...selectedRole, [a.id]: e.target.value })}>
                        {GRANTABLE_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                      </select>
                      <button className="btn btn-primary btn-sm" onClick={() => approve.mutate({ id: a.id, role: selectedRole[a.id] || a.position_applied_for })}>
                        Approve
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => changeStatus.mutate({ id: a.id, status: "rejected" })}>Reject</button>
                      <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: a.id, status: "under_review" })}>Mark under review</button>
                    </>
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
