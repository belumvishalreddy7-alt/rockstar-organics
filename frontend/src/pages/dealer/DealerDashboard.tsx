import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";

interface DealerProfileOut {
  id: string; business_name: string; district: string; directory_opt_in: boolean; farmer_case_opt_in: boolean;
  show_public_phone: boolean; show_public_email: boolean; public_phone: string | null; public_email: string | null;
  service_areas: { id: string; district: string; mandal: string | null }[];
}

export function DealerDashboard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["dealer-profile"], queryFn: () => api.get<DealerProfileOut>("/dealers/me/profile") });
  const [saved, setSaved] = useState(false);

  const updateProfile = useMutation({
    mutationFn: (payload: Partial<DealerProfileOut>) => api.put("/dealers/me/profile", payload),
    onSuccess: () => {
      setSaved(true);
      qc.invalidateQueries({ queryKey: ["dealer-profile"] });
    },
  });

  if (isLoading || !data) return <div className="loading-state">Loading your dealer profile...</div>;

  return (
    <div className="container page-section">
      <h1>{data.business_name}</h1>
      <p className="muted">District: {data.district}</p>

      <div className="panel">
        <h2>Visibility settings</h2>
        {saved && <div className="alert alert-success">Saved.</div>}
        <div className="stack">
          <label><input type="checkbox" checked={data.directory_opt_in}
            onChange={(e) => updateProfile.mutate({ directory_opt_in: e.target.checked })} /> Show my business in the public dealer directory</label>
          <label><input type="checkbox" checked={data.farmer_case_opt_in}
            onChange={(e) => updateProfile.mutate({ farmer_case_opt_in: e.target.checked })} /> Receive matched farmer support cases</label>
          <label><input type="checkbox" checked={data.show_public_phone}
            onChange={(e) => updateProfile.mutate({ show_public_phone: e.target.checked })} /> Show my phone number publicly</label>
          <label><input type="checkbox" checked={data.show_public_email}
            onChange={(e) => updateProfile.mutate({ show_public_email: e.target.checked })} /> Show my email publicly</label>
        </div>
      </div>

      <div className="panel">
        <h2>Service areas</h2>
        {data.service_areas.length === 0 ? (
          <EmptyState title="No service areas configured yet." />
        ) : (
          <ul>
            {data.service_areas.map((a) => <li key={a.id}>{a.district}{a.mandal ? ` — ${a.mandal}` : ""}</li>)}
          </ul>
        )}
      </div>
    </div>
  );
}
