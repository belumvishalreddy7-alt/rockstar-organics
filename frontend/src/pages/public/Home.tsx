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
            <Link className="btn btn-secondary" to="/login" style={{ background: "transparent", color: "#fff", borderColor: "#fff" }}>
              Login
            </Link>
            <Link className="btn btn-secondary" to="/dealer-programme" style={{ background: "transparent", color: "#fff", borderColor: "#fff" }}>
              Become a Dealer
            </Link>
            <Link className="btn btn-secondary" to="/distributors" style={{ background: "transparent", color: "#fff", borderColor: "#fff" }}>
              Become a Distributor
            </Link>
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
