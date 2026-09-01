import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../context/AuthContext";

interface AccountRow { id: string; email: string; full_name: string; status: string; created_at: string; }
interface StaffRow { id: string; email: string; full_name: string; role: string; status: string; }

const INVITABLE_ROLES: { value: string; label: string }[] = [
  { value: "admin", label: "Manager (Admin)" },
  { value: "content_manager", label: "Content Manager" },
  { value: "sales_manager", label: "Sales Manager" },
  { value: "field_officer", label: "Field Officer" },
];

function AccountTable({ kind }: { kind: "farmers" | "dealers" | "distributors" }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["accounts", kind], queryFn: () => api.get<AccountRow[]>(`/accounts/${kind}`) });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/accounts/${kind}/${id}/status/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts", kind] }),
  });

  const removeAccount = useMutation({
    mutationFn: (id: string) => api.del(`/accounts/${kind}/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts", kind] }),
  });

  if (isLoading) return <div className="loading-state">Loading accounts...</div>;
  if (!data || data.length === 0) return <EmptyState title={`No ${kind} accounts yet.`} />;

  // Suspend already removes a dealer/distributor from their public
  // directory immediately (reversible). Delete goes further: it
  // permanently removes their business profile, not just their ability
  // to log in - only the owner can do that, and only for these two kinds
  // (there's no equivalent profile to delete for a farmer account).
  const canDelete = user?.role === "super_admin" && kind !== "farmers";

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
                {canDelete && (
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => {
                      if (window.confirm(`Permanently delete ${a.full_name}'s business profile? Their login is disabled too. This cannot be undone.`)) removeAccount.mutate(a.id);
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
  );
}

function InviteStaffForm({ canCreateSuperAdmin, onInvited }: { canCreateSuperAdmin: boolean; onInvited: () => void }) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState(INVITABLE_ROLES[0].value);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ email: string; temporary_password: string } | null>(null);

  const invite = useMutation({
    mutationFn: () => api.post<{ email: string; temporary_password: string }>("/staff/invite", { email, full_name: fullName, role }),
    onSuccess: (data) => {
      setResult(data);
      setError(null);
      setEmail("");
      setFullName("");
      onInvited();
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Could not create the account."),
  });

  const roleOptions = canCreateSuperAdmin
    ? [{ value: "super_admin", label: "Owner (Super Administrator)" }, ...INVITABLE_ROLES]
    : INVITABLE_ROLES;

  return (
    <div className="panel">
      <h3>Invite a staff member</h3>
      <p className="small muted">
        Creates a real login for an owner/manager-level account. A one-time temporary password is generated here and
        shown only to you below - copy it and share it securely with the new account holder. They must change it on
        first login.
      </p>
      {error && <div className="alert alert-error">{error}</div>}
      {result && (
        <div className="alert alert-success">
          Account created for <strong>{result.email}</strong>. Temporary password (shown once):{" "}
          <code>{result.temporary_password}</code>
        </div>
      )}
      <form onSubmit={(e) => { e.preventDefault(); setResult(null); invite.mutate(); }}>
        <div className="grid cols-2">
          <div className="field">
            <label htmlFor="staff-full-name">Full name</label>
            <input id="staff-full-name" type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="staff-email">Email</label>
            <input id="staff-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="staff-role">Role</label>
            <select id="staff-role" value={role} onChange={(e) => setRole(e.target.value)}>
              {roleOptions.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
        </div>
        <button className="btn btn-primary" type="submit" disabled={invite.isPending}>Create account</button>
      </form>
    </div>
  );
}

function StaffPanel({ canCreateSuperAdmin }: { canCreateSuperAdmin: boolean }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["staff-accounts"], queryFn: () => api.get<StaffRow[]>("/staff") });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/staff/${id}/status/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["staff-accounts"] }),
  });

  return (
    <div>
      <InviteStaffForm canCreateSuperAdmin={canCreateSuperAdmin} onInvited={() => qc.invalidateQueries({ queryKey: ["staff-accounts"] })} />
      <h3>Existing staff accounts</h3>
      {isLoading && <div className="loading-state">Loading staff accounts...</div>}
      {data && data.length === 0 && <EmptyState title="No staff accounts yet." />}
      {data && data.length > 0 && (
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.id}>
                  <td>{s.full_name}</td><td>{s.email}</td><td>{s.role.replace("_", " ")}</td><td><StatusBadge status={s.status} /></td>
                  <td className="inline">
                    {s.status !== "active" && <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: s.id, status: "active" })}>Reactivate</button>}
                    {s.status !== "suspended" && <button className="btn btn-danger btn-sm" onClick={() => changeStatus.mutate({ id: s.id, status: "suspended" })}>Suspend</button>}
                    {s.status !== "disabled" && <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: s.id, status: "disabled" })}>Disable</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function AccountManagement() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"farmers" | "dealers" | "distributors" | "staff">("farmers");
  const isSuperAdminOrAdmin = user && ["super_admin", "admin"].includes(user.role);

  return (
    <div>
      <h2>Account management</h2>
      <p className="small muted">Suspending a dealer or distributor account also removes them from their public directory immediately.</p>
      <div className="inline" style={{ marginBottom: 16 }}>
        {isSuperAdminOrAdmin && <button className={`btn btn-sm ${tab === "farmers" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("farmers")}>Farmer accounts</button>}
        <button className={`btn btn-sm ${tab === "dealers" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("dealers")}>Dealer accounts</button>
        <button className={`btn btn-sm ${tab === "distributors" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("distributors")}>Distributor accounts</button>
        {isSuperAdminOrAdmin && <button className={`btn btn-sm ${tab === "staff" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("staff")}>Staff accounts</button>}
      </div>
      {tab === "staff" && isSuperAdminOrAdmin ? (
        <StaffPanel canCreateSuperAdmin={user?.role === "super_admin"} />
      ) : tab === "farmers" && isSuperAdminOrAdmin ? (
        <AccountTable kind="farmers" />
      ) : tab === "distributors" ? (
        <AccountTable kind="distributors" />
      ) : (
        <AccountTable kind="dealers" />
      )}
    </div>
  );
}
