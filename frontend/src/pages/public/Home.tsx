import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { useLanguage } from "../../context/LanguageContext";
import { localizedProductField, type ProductTranslations } from "../../i18n/localized";

interface Product { id: string; name: string; slug: string; short_description: string | null; translations: ProductTranslations; }

export function Home() {
  const { language, t } = useLanguage();
  const products = useQuery({
    queryKey: ["home-products"],
    queryFn: () => api.get<{ items: Product[] }>("/products/public?page_size=3"),
  });

  return (
    <>
      <section className="hero">
        <div className="hero-art" aria-hidden="true">
          <svg viewBox="0 0 1600 500" preserveAspectRatio="xMidYMid slice">
            <defs>
              <linearGradient id="heroSky" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3d6b4c" />
                <stop offset="100%" stopColor="#12362b" />
              </linearGradient>
              <radialGradient id="heroSun" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#f2c96b" stopOpacity="0.55" />
                <stop offset="100%" stopColor="#f2c96b" stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect width="1600" height="500" fill="url(#heroSky)" />
            <circle cx="1280" cy="120" r="150" fill="url(#heroSun)" />
            <ellipse cx="800" cy="560" rx="1300" ry="220" fill="#1f4d2b" opacity="0.7" />
            <ellipse cx="400" cy="580" rx="1100" ry="180" fill="#245c34" opacity="0.7" />
            <path d="M0,430 C300,390 600,450 900,410 C1200,370 1400,430 1600,400 L1600,500 L0,500 Z" fill="#0c2a1d" />
            <g opacity="0.18" stroke="#eef1de" strokeWidth="3" fill="none">
              <path d="M0,450 C300,410 600,470 900,430 C1200,390 1400,450 1600,420" />
              <path d="M0,470 C300,430 600,490 900,450 C1200,410 1400,470 1600,440" />
            </g>
          </svg>
        </div>
        <div className="hero-fade" aria-hidden="true"></div>
        <div className="container">
          <h1>{t("home.heroTitle")}</h1>
          <p><strong>{t("home.heroLead")}</strong></p>
          <p>{t("home.heroBody")}</p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/products">{t("home.exploreProducts")}</Link>
            <Link className="btn btn-outline-light" to="/dealer-programme">{t("home.becomeDealer")}</Link>
            <Link className="btn btn-outline-light" to="/distributors">{t("home.becomeDistributor")}</Link>
            <Link className="btn btn-outline-light" to="/login">{t("home.login")}</Link>
          </div>
        </div>
      </section>

      <section className="page-section">
        <div className="container">
          <h2>{t("home.builtAroundTitle")}</h2>
          <p>{t("home.builtAroundBody")}</p>
        </div>
      </section>

      <section className="page-section">
        <div className="container">
          <div className="section-heading">
            <h2>{t("home.exploreProductsTitle")}</h2>
            <Link to="/products">{t("home.viewFullCatalogue")}</Link>
          </div>
          <p className="small muted">{t("home.workflowNote")}</p>
          {products.isLoading && <div className="loading-state">Loading products...</div>}
          {products.data && products.data.items.length === 0 && (
            <EmptyState title={t("home.noProducts")}>
              <p className="small">{t("home.noProductsBody")}</p>
            </EmptyState>
          )}
          <div className="grid cols-3">
            {products.data?.items.map((p) => (
              <div className="panel" key={p.id}>
                <h3><Link to={`/products/${p.slug}`}>{localizedProductField(p, language, "name") || p.name}</Link></h3>
                <p className="small muted">{localizedProductField(p, language, "short_description") || t("home.pendingVerification")}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="page-section tight" style={{ background: "var(--color-surface-alt)" }}>
        <div className="container">
          <h2>{t("home.infoEarnsTitle")}</h2>
          <p className="small">
            {t("home.infoEarnsBody")}
            <em> {t("home.pendingVerification")}</em>
          </p>
        </div>
      </section>
    </>
  );
}
