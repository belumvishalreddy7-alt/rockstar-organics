import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";

interface DealerEntry {
  id: string; business_name: string; district: string;
  service_areas: { district: string; mandal: string | null }[];
  public_phone: string | null; public_email: string | null; last_activity_at: string | null;
}

export function DealerDirectory() {
  const [district, setDistrict] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["dealer-directory", district],
    queryFn: () => api.get<DealerEntry[]>(`/dealers/directory${district ? `?district=${encodeURIComponent(district)}` : ""}`),
  });

  return (
    <div className="container page-section">
      <h1>Dealer directory</h1>
      <p className="muted">Only active, approved dealers who have opted into the public directory are listed here.</p>
      <div className="field" style={{ maxWidth: 320 }}>
        <label htmlFor="district">District</label>
        <input type="text" id="district" value={district} onChange={(e) => setDistrict(e.target.value)} placeholder="e.g. Hyderabad" />
      </div>

      {isLoading && <div className="loading-state">Loading dealers...</div>}
      {data && data.length === 0 && (
        <EmptyState title="No participating dealers found for this search.">
          <p className="small">Try a different district, or check back later as more dealers join the directory.</p>
        </EmptyState>
      )}
      <div className="grid cols-2">
        {data?.map((d) => (
          <div className="panel" key={d.id}>
            <h3>{d.business_name}</h3>
            <p className="small muted">
              Service areas: {d.service_areas.map((a) => a.mandal ? `${a.district} - ${a.mandal}` : a.district).join(", ") || "Not specified"}
            </p>
            {d.public_phone && <p className="small">Phone: {d.public_phone}</p>}
            {d.public_email && <p className="small">Email: {d.public_email}</p>}
            {d.last_activity_at && <p className="small muted">Last confirmed activity: {new Date(d.last_activity_at).toLocaleDateString()}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
