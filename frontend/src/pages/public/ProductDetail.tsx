import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, mediaUrl } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";

interface ReviewItem { id: string; reviewer_name: string; rating: number; comment: string | null; created_at: string; }
interface RatingBreakdown { "1": number; "2": number; "3": number; "4": number; "5": number; }
interface ProductOut {
  id: string; name: string; short_description: string | null; full_description: string | null;
  benefits: string | null; recommended_crops: string | null; application_method: string | null;
  dosage_value: string | null; dosage_unit: string | null;
  manufacturing_date: string | null; expiry_date: string | null;
  precautions: string | null; average_rating: number | null; approved_review_count: number;
  rating_breakdown: RatingBreakdown; reviews: ReviewItem[];
  images: { id: string; file_path: string; alt_text: string | null }[];
  category_id: string | null;
  category_name: string | null;
}

/** Renders a 5-star row for a given average - real data only, this never
 * shows a rating figure that didn't come from the API. */
function StarRow({ value, size = 18 }: { value: number; size?: number }) {
  return (
    <span aria-hidden="true" style={{ display: "inline-flex", gap: 1, fontSize: size, lineHeight: 1, color: "var(--color-accent)" }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} style={{ opacity: value >= n ? 1 : value > n - 1 ? 0.5 : 0.25 }}>★</span>
      ))}
    </span>
  );
}

function ImageGallery({ images, productName }: { images: ProductOut["images"]; productName: string }) {
  const [active, setActive] = useState(0);
  if (images.length === 0) {
    return (
      <div
        className="panel"
        style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 260, color: "var(--color-text-muted)" }}
      >
        Information pending verification.
      </div>
    );
  }
  const current = images[Math.min(active, images.length - 1)];
  const src = (img: ProductOut["images"][number]) => mediaUrl(`/api/v1/media/public/${img.file_path.replace(/^public\//, "")}`);

  return (
    <div>
      <div style={{ position: "relative", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
        <img
          src={src(current)}
          alt={current.alt_text || productName}
          style={{ width: "100%", aspectRatio: "1 / 1", objectFit: "contain", display: "block" }}
        />
        {images.length > 1 && (
          <>
            <button
              type="button" aria-label="Previous image"
              onClick={() => setActive((a) => (a - 1 + images.length) % images.length)}
              className="btn btn-ghost btn-sm"
              style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)", background: "var(--color-surface)" }}
            >
              ‹
            </button>
            <button
              type="button" aria-label="Next image"
              onClick={() => setActive((a) => (a + 1) % images.length)}
              className="btn btn-ghost btn-sm"
              style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", background: "var(--color-surface)" }}
            >
              ›
            </button>
          </>
        )}
      </div>
      {images.length > 1 && (
        <div className="inline" style={{ marginTop: 10, flexWrap: "wrap" }}>
          {images.map((img, i) => (
            <button
              key={img.id} type="button" onClick={() => setActive(i)} aria-label={`Show image ${i + 1}`}
              style={{
                padding: 0, width: 56, height: 56, borderRadius: "var(--radius-sm)", overflow: "hidden", cursor: "pointer",
                border: i === active ? "2px solid var(--color-green-700)" : "1px solid var(--color-border)", background: "none",
              }}
            >
              <img src={src(img)} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ProductDetail() {
  const { slug } = useParams();
  const qc = useQueryClient();
  const { user } = useAuth();
  const [form, setForm] = useState({ rating: 5, comment: "" });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["product", slug],
    queryFn: () => api.get<ProductOut>(`/products/public/${slug}`),
  });

  const submitReview = useMutation({
    mutationFn: () => api.post(`/reviews/products/${data?.id}`, form),
    onSuccess: () => {
      setSubmitted(true);
      setError(null);
      qc.invalidateQueries({ queryKey: ["product", slug] });
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  useDocumentTitle(data ? `${data.name} | Rockstar Organics` : "Product | Rockstar Organics");

  if (isLoading) return <div className="container page-section loading-state">Loading product...</div>;
  if (isError || !data) return <div className="container page-section"><div className="alert alert-error">Product not found or not published.</div></div>;

  const breakdown = data.rating_breakdown;
  const keyFacts: [string, string][] = [
    ...(data.recommended_crops ? [["Recommended crops", data.recommended_crops] as [string, string]] : []),
    ...(data.application_method ? [["Application method", data.application_method] as [string, string]] : []),
    ...(data.dosage_value ? [["Dosage", `${data.dosage_value} ${data.dosage_unit || ""}`.trim()] as [string, string]] : []),
    ...(data.manufacturing_date ? [["Manufacturing date", new Date(data.manufacturing_date).toLocaleDateString()] as [string, string]] : []),
    ...(data.expiry_date ? [["Expiry date", new Date(data.expiry_date).toLocaleDateString()] as [string, string]] : []),
  ];

  return (
    <div className="container page-section">
      <nav aria-label="Breadcrumb" className="small muted" style={{ marginBottom: 16 }}>
        <Link to="/">Home</Link>
        {" / "}
        <Link to="/products">Products</Link>
        {data.category_name && data.category_id && (
          <>
            {" / "}
            <Link to={`/products?category_id=${encodeURIComponent(data.category_id)}`}>{data.category_name}</Link>
          </>
        )}
        {" / "}
        <span>{data.name}</span>
      </nav>

      <div className="grid cols-2" style={{ alignItems: "start", marginBottom: 24 }}>
        <ImageGallery images={data.images} productName={data.name} />

        <div>
          <p className="small muted" style={{ textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>Rockstar Organics</p>
          <h1 style={{ marginBottom: 8 }}>{data.name}</h1>
          <div className="inline" style={{ marginBottom: 10 }}>
            {data.approved_review_count > 0 ? (
              <>
                <StarRow value={data.average_rating || 0} />
                <span className="small">{data.average_rating?.toFixed(1)}</span>
                <span className="small muted">
                  ({data.approved_review_count} verified farmer review{data.approved_review_count === 1 ? "" : "s"})
                </span>
              </>
            ) : (
              <span className="small muted">No farmer reviews yet</span>
            )}
          </div>
          {data.short_description && <p className="muted">{data.short_description}</p>}

          {keyFacts.length > 0 && (
            <table className="data-table" style={{ margin: "16px 0" }}>
              <tbody>
                {keyFacts.map(([label, value]) => (
                  <tr key={label}><th style={{ width: "45%" }}>{label}</th><td>{value}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="grid cols-2">
        <div className="panel">
          <h2>Product information</h2>
          <p>{data.full_description || "Information pending verification."}</p>
          {data.benefits && <><h3>Uses &amp; benefits</h3><p>{data.benefits}</p></>}
          {data.precautions && <><h3>Precautions</h3><p>{data.precautions}</p></>}
        </div>

        <div className="panel">
          <h2>Farmer ratings &amp; reviews</h2>
          {data.approved_review_count > 0 && breakdown && (
            <ul className="small muted" style={{ listStyle: "none", padding: 0, marginBottom: 12 }}>
              {([5, 4, 3, 2, 1] as const).map((star) => (
                <li key={star}>{star} star: {breakdown[String(star) as keyof RatingBreakdown]}</li>
              ))}
            </ul>
          )}
          <ul className="stack" style={{ listStyle: "none", padding: 0 }}>
            {data.reviews.map((r) => (
              <li key={r.id} className="panel">
                <strong>{r.reviewer_name}</strong> — {r.rating}/5
                {r.comment && <p className="small">{r.comment}</p>}
              </li>
            ))}
          </ul>

          <h3>Submit a rating</h3>
          {user?.role !== "farmer" ? (
            <p className="small muted">
              {user
                ? "Only farmer accounts can submit product ratings."
                : <>Sign in to a farmer account to leave a rating. <Link to="/login">Sign in</Link> or <Link to="/signup">create an account</Link>.</>}
            </p>
          ) : submitted ? (
            <div className="alert alert-success">Thank you. Your review will appear once approved by staff.</div>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                submitReview.mutate();
              }}
            >
              {error && <div className="alert alert-error">{error}</div>}
              <div className="field">
                <label htmlFor="rating">Rating</label>
                <select id="rating" value={form.rating} onChange={(e) => setForm({ ...form, rating: Number(e.target.value) })}>
                  {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} of 5</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="comment">Comment (optional)</label>
                <textarea id="comment" value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} />
              </div>
              <button className="btn btn-primary" type="submit" disabled={submitReview.isPending}>
                {submitReview.isPending ? "Submitting..." : "Submit rating"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
