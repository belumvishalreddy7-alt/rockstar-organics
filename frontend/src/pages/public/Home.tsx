import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";

interface Product { id: string; name: string; slug: string; short_description: string | null; }

export function Home() {
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
          <h1>Agriculture. Trust. Transparency.</h1>
          <p>
            <strong>
              Trust density beats clever copy in agri &mdash; farmers buy from people they believe, not brands they
              like.
            </strong>
          </p>
          <p>
            Rockstar Organics is an agricultural enterprise rooted in Telangana, India, serving the farming
            community across Ranga Reddy district and beyond.
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/products">Explore Products</Link>
            <Link className="btn btn-outline-light" to="/dealer-programme">Become a Dealer</Link>
            <Link className="btn btn-outline-light" to="/distributors">Become a Distributor</Link>
            <Link className="btn btn-outline-light" to="/login">Login</Link>
          </div>
        </div>
      </section>

      <section className="page-section">
        <div className="container">
          <h2>Built around the farming community</h2>
          <p>
            Rockstar Organics connects farmers, dealers, distributors, field officers and administrators through a
            unified digital platform. The platform is designed to make agricultural products and verified
            information easier to discover while providing structured workflows for enquiries, stock availability,
            support cases, field visits and business relationships.
          </p>
        </div>
      </section>

      <section className="page-section">
        <div className="container">
          <div className="section-heading">
            <h2>Explore Products</h2>
            <Link to="/products">View full catalogue</Link>
          </div>
          <p className="small muted">
            Every public product record follows a controlled workflow before publication: Draft &rarr; Review
            &rarr; Approval &rarr; Publication. Only approved and published product information appears publicly.
          </p>
          {products.isLoading && <div className="loading-state">Loading products...</div>}
          {products.data && products.data.items.length === 0 && (
            <EmptyState title="No products have been published yet.">
              <p className="small">Products appear here once staff review and publish them.</p>
            </EmptyState>
          )}
          <div className="grid cols-3">
            {products.data?.items.map((p) => (
              <div className="panel" key={p.id}>
                <h3><Link to={`/products/${p.slug}`}>{p.name}</Link></h3>
                <p className="small muted">{p.short_description || "Information pending verification."}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="page-section tight" style={{ background: "var(--color-surface-alt)" }}>
        <div className="container">
          <h2>Information should earn its place</h2>
          <p className="small">
            Agricultural product information can influence farming decisions. Product records can contain
            composition, formulation, application, dosage, precautions, packaging, label information, technical
            documents, supporting documents and source information. Unverified information remains
            <em> Information pending verification.</em>
          </p>
        </div>
      </section>
    </>
  );
}
