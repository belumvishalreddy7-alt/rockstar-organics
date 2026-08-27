import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useLocation } from "react-router-dom";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface CaseSummary { id: string; reference_number: string; title: string; status: string; created_at: string; }
interface VisitSummary { id: string; reference_number: string; status: string; scheduled_start: string | null; }

export function FarmerDashboardLayout() {
  const { user } = useAuth();
  const location = useLocation();
  return (
    <div className="container page-section">
      <h1>Welcome, {user?.full_name}</h1>
      <div className="dashboard-layout">
        <nav className="dashboard-nav" aria-label="Farmer account navigation">
          <Link className={location.pathname === "/farmer" ? "active" : ""} to="/farmer">My cases</Link>
          <Link className={location.pathname === "/farmer/visits" ? "active" : ""} to="/farmer/visits">My field visits</Link>
          <Link className={location.pathname === "/farmer/cases/new" ? "active" : ""} to="/farmer/cases/new">Submit new case</Link>
        </nav>
        <div><Outlet /></div>
      </div>
    </div>
  );
}

export function FarmerCaseList() {
  const { data, isLoading } = useQuery({ queryKey: ["my-cases"], queryFn: () => api.get<CaseSummary[]>("/cases/mine") });
  if (isLoading) return <div className="loading-state">Loading your cases...</div>;
  if (!data || data.length === 0) {
    return (
      <EmptyState title="You have not submitted any support cases yet.">
        <Link className="btn btn-primary" to="/farmer/cases/new">Submit your first case</Link>
      </EmptyState>
    );
  }
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead><tr><th>Reference</th><th>Title</th><th>Status</th><th>Submitted</th></tr></thead>
        <tbody>
          {data.map((c) => (
            <tr key={c.id}>
              <td><Link to={`/farmer/cases/${c.id}`}>{c.reference_number}</Link></td>
              <td>{c.title}</td>
              <td><StatusBadge status={c.status} /></td>
              <td>{new Date(c.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FarmerVisitList() {
  const { data, isLoading } = useQuery({ queryKey: ["my-visits"], queryFn: () => api.get<VisitSummary[]>("/visits/mine") });
  if (isLoading) return <div className="loading-state">Loading your visits...</div>;
  if (!data || data.length === 0) return <EmptyState title="No field visits requested yet." />;
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead><tr><th>Reference</th><th>Status</th><th>Scheduled</th></tr></thead>
        <tbody>
          {data.map((v) => (
            <tr key={v.id}>
              <td>{v.reference_number}</td>
              <td><StatusBadge status={v.status} /></td>
              <td>{v.scheduled_start ? new Date(v.scheduled_start).toLocaleString() : "Not yet scheduled"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
