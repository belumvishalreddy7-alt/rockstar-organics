import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, mediaUrl } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";

interface AgriculturePhoto {
  id: string; title: string; caption: string | null; category: string;
  location: string; crop: string; photo_date: string; photographer_source: string;
  alt_text: string; image_url: string;
}

const CATEGORIES = [
  "farmers", "farms", "fields", "crops", "product_application", "dealer_network",
  "distributor_network", "field_visits", "agricultural_activities",
  "company_facilities", "manufacturing", "research", "community_activities",
];

export function Gallery() {
  const [category, setCategory] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["agriculture-gallery", category],
    queryFn: () => api.get<AgriculturePhoto[]>(`/media/agriculture${category ? `?category=${category}` : ""}`),
  });

  return (
    <div className="container page-section">
      <h1>Agriculture photo gallery</h1>
      <p className="muted">
        Photographs published here are owned by Rockstar Organics or licensed/authorized for website use.
        Location, crop, date and photographer details show "Information pending verification." until confirmed
        rather than being invented.
      </p>
      <div className="field" style={{ maxWidth: 280 }}>
        <label htmlFor="category">Category</label>
        <select id="category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
        </select>
      </div>
      {isLoading && <div className="loading-state">Loading photos...</div>}
      {data && data.length === 0 && <EmptyState title="No photographs are published yet." />}
      <div className="grid cols-3">
        {data?.map((p) => (
          <div className="panel" key={p.id}>
            <img
              src={mediaUrl(p.image_url)}
              alt={p.alt_text}
              style={{ width: "100%", height: 180, objectFit: "cover", borderRadius: 8, marginBottom: 8 }}
              loading="lazy"
            />
            <h3>{p.title}</h3>
            {p.caption && <p className="small">{p.caption}</p>}
            <p className="small muted">Location: {p.location}</p>
            <p className="small muted">Crop: {p.crop}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
