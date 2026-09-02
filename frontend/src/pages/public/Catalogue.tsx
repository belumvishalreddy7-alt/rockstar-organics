import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api, mediaUrl } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { useLanguage } from "../../context/LanguageContext";
import { localizedProductField, type ProductTranslations } from "../../i18n/localized";

interface Product {
  id: string; name: string; slug: string; short_description: string | null;
  average_rating: number | null; approved_review_count: number;
  category_name: string | null;
  images: { id: string; file_path: string; alt_text: string | null }[];
  translations: ProductTranslations;
}

export function Catalogue() {
  const { language, t } = useLanguage();
  const [searchParams] = useSearchParams();
  const categoryId = searchParams.get("category_id");
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(1);

  useState(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 400);
    return () => clearTimeout(timer);
  });

  const { data, isLoading } = useQuery({
    queryKey: ["catalogue", debouncedQ, page, categoryId],
    queryFn: () =>
      api.get<{ total: number; items: Product[] }>(
        `/products/public?page=${page}&page_size=12${debouncedQ ? `&q=${encodeURIComponent(debouncedQ)}` : ""}${categoryId ? `&category_id=${encodeURIComponent(categoryId)}` : ""}`
      ),
  });

  return (
    <div className="container page-section">
      <div className="section-heading">
        <h1>{t("catalogue.title")}</h1>
      </div>
      {categoryId && data && data.items[0]?.category_name && (
        <p className="small muted">
          {t("catalogue.showing")} <strong>{data.items[0].category_name}</strong> · <Link to="/products">{t("catalogue.viewAll")}</Link>
        </p>
      )}
      <div className="field" style={{ maxWidth: 360 }}>
        <label htmlFor="catalogue-search">{t("catalogue.searchLabel")}</label>
        <input
          id="catalogue-search"
          type="text"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          placeholder={t("catalogue.searchPlaceholder")}
        />
      </div>

      {isLoading && <div className="loading-state">Loading catalogue...</div>}
      {data && data.items.length === 0 && (
        <EmptyState title={t("catalogue.noMatch")}>
          <p className="small">{t("catalogue.tryDifferent")}</p>
        </EmptyState>
      )}
      <div className="grid cols-3">
        {data?.items.map((p) => {
          const name = localizedProductField(p, language, "name") || p.name;
          const shortDescription = localizedProductField(p, language, "short_description");
          return (
          <div className="panel" key={p.id}>
            {p.images[0] && (
              <img
                src={mediaUrl(`/api/v1/media/public/${p.images[0].file_path.replace(/^public\//, "")}`)}
                alt={p.images[0].alt_text || name}
                style={{ width: "100%", aspectRatio: "1 / 1", objectFit: "contain", borderRadius: "var(--radius-sm)", marginBottom: 10, background: "var(--color-surface-alt)" }}
              />
            )}
            {p.category_name && <p className="small muted" style={{ margin: "0 0 2px" }}>{p.category_name}</p>}
            <h3><Link to={`/products/${p.slug}`}>{name}</Link></h3>
            <p className="small muted">{shortDescription || "No short description provided."}</p>
            <p className="small">
              {p.approved_review_count > 0
                ? `${p.average_rating?.toFixed(1)} average rating (${p.approved_review_count} reviews)`
                : t("catalogue.noApprovedReviews")}
            </p>
          </div>
          );
        })}
      </div>
      {data && data.total > 12 && (
        <div className="inline" style={{ marginTop: 20 }}>
          <button className="btn btn-secondary btn-sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>{t("catalogue.previous")}</button>
          <span className="small muted">{t("catalogue.page")} {page}</span>
          <button className="btn btn-secondary btn-sm" disabled={page * 12 >= data.total} onClick={() => setPage((p) => p + 1)}>{t("catalogue.next")}</button>
        </div>
      )}
    </div>
  );
}
