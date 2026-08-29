import { Link, Outlet, useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../../components/EmptyState";

interface Metrics {
  draft_products: number; products_in_review: number; published_products: number; new_dealer_applications: number;
  open_support_cases: number; high_priority_cases: number; upcoming_field_visits: number; pending_reviews: number;
  open_enquiries: number; overdue_tasks: number; published_knowledge_articles: number; failed_notifications: number;
}

interface NotificationOut {
  id: string; type: string; title: string; message: string; is_read: boolean; created_at: string;
}

export function StaffDashboardLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const isAdmin = user && ["super_admin", "admin"].includes(user.role);
  const links = [
    { to: "/staff", label: "Overview" },
    { to: "/staff/products", label: "Products" },
    { to: "/staff/dealer-applications", label: "Dealer applications" },
    { to: "/staff/distributor-applications", label: "Distributor applications" },
    { to: "/staff/documents", label: "Certificates & documents" },
    { to: "/staff/gallery", label: "Agriculture gallery" },
    { to: "/staff/cases", label: "Farmer cases" },
    { to: "/staff/reviews", label: "Product reviews" },
    { to: "/staff/announcements", label: "Announcements" },
    { to: "/staff/knowledge", label: "Knowledge articles" },
    { to: "/staff/tasks", label: "Follow-up tasks" },
    { to: "/staff/enquiries", label: "Enquiries" },
    { to: "/staff/my-visits", label: "My assigned visits" },
    { to: "/staff/accounts", label: "Accounts" },
  ];
  return (
    <div className="container page-section">
      <h1>Staff dashboard</h1>
      <p className="muted">Signed in as {user?.full_name} ({user?.role.replace("_", " ")})</p>
      <div className="dashboard-layout">
        <nav className="dashboard-nav" aria-label="Staff navigation">
          {links.map((l) => (
            <Link key={l.to} className={location.pathname === l.to ? "active" : ""} to={l.to}>{l.label}</Link>
          ))}
        </nav>
        <div>{location.pathname === "/staff" ? (isAdmin ? <Overview /> : <RoleQueue />) : <Outlet />}</div>
      </div>
    </div>
  );
}

function Overview() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard-metrics"], queryFn: () => api.get<Metrics>("/reports/dashboard-metrics") });
  if (isLoading || !data) return <div className="loading-state">Loading metrics...</div>;
  const tiles: [string, number][] = [
    ["Draft products", data.draft_products], ["Products in review", data.products_in_review],
    ["Published products", data.published_products], ["New dealer applications", data.new_dealer_applications],
    ["Open support cases", data.open_support_cases], ["High priority cases", data.high_priority_cases],
    ["Upcoming field visits", data.upcoming_field_visits], ["Pending reviews", data.pending_reviews],
    ["Open enquiries", data.open_enquiries], ["Overdue tasks", data.overdue_tasks],
    ["Published knowledge articles", data.published_knowledge_articles], ["Failed notifications", data.failed_notifications],
  ];
  return (
    <>
      <h2>Operational metrics</h2>
      <p className="small muted">All values are computed directly from the database.</p>
      <div className="metric-row">
        {tiles.map(([label, value]) => (
          <div className="metric-tile" key={label}><div className="value">{value}</div><div className="label">{label}</div></div>
        ))}
      </div>
      <Notifications />
    </>
  );
}

function Notifications() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["notifications"], queryFn: () => api.get<NotificationOut[]>("/notifications") });
  const markRead = useMutation({
    mutationFn: (id: string) => api.post(`/notifications/${id}/read`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const unreadCount = data?.filter((n) => !n.is_read).length ?? 0;

  return (
    <div className="panel">
      <div className="section-heading">
        <h2>Notifications{unreadCount > 0 ? ` (${unreadCount} unread)` : ""}</h2>
      </div>
      {isLoading && <div className="loading-state">Loading notifications...</div>}
      {data && data.length === 0 && <EmptyState title="No notifications yet." />}
      {data && data.length > 0 && (
        <ul>
          {data.map((n) => (
            <li key={n.id} style={{ fontWeight: n.is_read ? "normal" : 600 }}>
              {n.title} - {n.message}
              <span className="muted"> ({new Date(n.created_at).toLocaleString()})</span>
              {!n.is_read && <button className="btn btn-ghost btn-sm" onClick={() => markRead.mutate(n.id)}>Mark read</button>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RoleQueue() {
  return (
    <div className="panel">
      <h2>Your work queue</h2>
      <p className="small muted">Use the navigation to review products, dealer applications, farmer cases, and pending reviews assigned to your role.</p>
    </div>
  );
}
