import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";

interface DistributorProfileOut {
  id: string; business_name: string; territory: string; public_phone: string | null; public_email: string | null;
  address: string | null; suspended: boolean;
}

interface StockRow { product_id: string; status: string; quantity_note: string | null; updated_at: string; }

export function DistributorDashboard() {
  const qc = useQueryClient();
  const [saved, setSaved] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["distributor-profile"], queryFn: () => api.get<DistributorProfileOut>("/distributors/me/profile") });
  const { data: stock } = useQuery({ queryKey: ["distributor-stock"], queryFn: () => api.get<StockRow[]>("/distributors/me/stock") });

  const updateProfile = useMutation({
    mutationFn: (payload: Partial<DistributorProfileOut>) => api.put("/distributors/me/profile", payload),
    onSuccess: () => {
      setSaved(true);
      qc.invalidateQueries({ queryKey: ["distributor-profile"] });
    },
  });

  if (isLoading || !data) return <div className="container page-section loading-state">Loading your distributor profile...</div>;

  return (
    <div className="container page-section">
      <h1>{data.business_name}</h1>
      <p className="muted">Territory: {data.territory}</p>
      {data.suspended && <div className="alert alert-error">This account is currently suspended. Contact Rockstar Organics staff.</div>}

      <div className="panel">
        <h2>Profile</h2>
        {saved && <div className="alert alert-success">Saved.</div>}
        <div className="field"><label htmlFor="territory">Territory</label>
          <input type="text" id="territory" value={data.territory} onChange={(e) => updateProfile.mutate({ territory: e.target.value })} /></div>
        <div className="field"><label htmlFor="public_phone">Public phone (optional)</label>
          <input type="text" id="public_phone" value={data.public_phone || ""} onChange={(e) => updateProfile.mutate({ public_phone: e.target.value })} /></div>
        <div className="field"><label htmlFor="public_email">Public email (optional)</label>
          <input type="text" id="public_email" value={data.public_email || ""} onChange={(e) => updateProfile.mutate({ public_email: e.target.value })} /></div>
      </div>

      <div className="panel">
        <h2>Declared stock</h2>
        {!stock || stock.length === 0 ? (
          <EmptyState title="No stock declared yet.">
            <p className="small">Stock is declared per published product from your product catalogue view.</p>
          </EmptyState>
        ) : (
          <table className="data-table">
            <thead><tr><th>Product</th><th>Status</th><th>Notes</th><th>Updated</th></tr></thead>
            <tbody>
              {stock.map((s) => (
                <tr key={s.product_id}>
                  <td>{s.product_id}</td><td>{s.status}</td><td>{s.quantity_note || "—"}</td>
                  <td>{new Date(s.updated_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
