import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../context/AuthContext";

interface AccountRow { id: string; email: string; full_name: string; status: string; created_at: string; }

function AccountTable({ kind }: { kind: "farmers" | "dealers" }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["accounts", kind], queryFn: () => api.get<AccountRow[]>(`/accounts/${kind}`) });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/accounts/${kind}/${id}/status/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts", kind] }),
  });

  if (isLoading) return <div className="loading-state">Loading accounts...</div>;
  if (!data || data.length === 0) return <EmptyState title={`No ${kind} accounts yet.`} />;

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {data.map((a) => (
            <tr key={a.id}>
              <td>{a.full_name}</td><td>{a.email}</td><td><StatusBadge status={a.status} /></td>
              <td className="inline">
                {a.status !== "active" && <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: a.id, status: "active" })}>Reactivate</button>}
                {a.status !== "suspended" && <button className="btn btn-danger btn-sm" onClick={() => changeStatus.mutate({ id: a.id, status: "suspended" })}>Suspend</button>}
                {a.status !== "disabled" && <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: a.id, status: "disabled" })}>Disable</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AccountManagement() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"farmers" | "dealers">("farmers");
  const isSuperAdminOrAdmin = user && ["super_admin", "admin"].includes(user.role);

  return (
    <div>
      <h2>Account management</h2>
      <p className="small muted">Suspending a dealer account also removes them from the public directory and farmer-case matching immediately.</p>
      <div className="inline" style={{ marginBottom: 16 }}>
        {isSuperAdminOrAdmin && <button className={`btn btn-sm ${tab === "farmers" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("farmers")}>Farmer accounts</button>}
        <button className={`btn btn-sm ${tab === "dealers" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("dealers")}>Dealer accounts</button>
      </div>
      {tab === "farmers" && isSuperAdminOrAdmin ? <AccountTable kind="farmers" /> : <AccountTable kind="dealers" />}
    </div>
  );
}
