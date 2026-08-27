import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";

interface Product {
  id: string; name: string; slug: string; short_description: string | null;
  average_rating: number | null; approved_review_count: number;
}

export function Catalogue() {
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(1);

  useState(() => {
    const t = setTimeout(() => setDebouncedQ(q), 400);
    return () => clearTimeout(t);
  });

  const { data, isLoading } = useQuery({
    queryKey: ["catalogue", debouncedQ, page],
    queryFn: () =>
      api.get<{ total: number; items: Product[] }>(`/products/public?page=${page}&page_size=12${debouncedQ ? `&q=${encodeURIComponent(debouncedQ)}` : ""}`),
  });

  return (
    <div className="container page-section">
      <div className="section-heading">
        <h1>Product catalogue</h1>
      </div>
      <div className="field" style={{ maxWidth: 360 }}>
        <label htmlFor="catalogue-search">Search products</label>
        <input
          id="catalogue-search"
          type="text"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          placeholder="Search by product name"
        />
      </div>

      {isLoading && <div className="loading-state">Loading catalogue...</div>}
      {data && data.items.length === 0 && (
        <EmptyState title="No published products match your search.">
          <p className="small">Try a different search term, or check back later.</p>
        </EmptyState>
      )}
      <div className="grid cols-3">
        {data?.items.map((p) => (
          <div className="panel" key={p.id}>
            <h3><Link to={`/products/${p.slug}`}>{p.name}</Link></h3>
            <p className="small muted">{p.short_description || "No short description provided."}</p>
            <p className="small">
              {p.approved_review_count > 0
                ? `${p.average_rating?.toFixed(1)} average rating (${p.approved_review_count} reviews)`
                : "No approved reviews yet."}
            </p>
          </div>
        ))}
      </div>
      {data && data.total > 12 && (
        <div className="inline" style={{ marginTop: 20 }}>
          <button className="btn btn-secondary btn-sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span className="small muted">Page {page}</span>
          <button className="btn btn-secondary btn-sm" disabled={page * 12 >= data.total} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}
