import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api, ApiError, mediaUrl } from "../../api/client";

interface ReviewItem { id: string; reviewer_name: string; rating: number; comment: string | null; created_at: string; }
interface ProductOut {
  id: string; name: string; short_description: string | null; full_description: string | null;
  benefits: string | null; recommended_crops: string | null; dosage_value: string | null; dosage_unit: string | null;
  precautions: string | null; average_rating: number | null; approved_review_count: number; reviews: ReviewItem[];
  images: { id: string; file_path: string; alt_text: string | null }[];
}

export function ProductDetail() {
  const { slug } = useParams();
  const qc = useQueryClient();
  const [form, setForm] = useState({ reviewer_name: "", rating: 5, comment: "" });
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

  if (isLoading) return <div className="container page-section loading-state">Loading product...</div>;
  if (isError || !data) return <div className="container page-section"><div className="alert alert-error">Product not found or not published.</div></div>;

  return (
    <div className="container page-section">
      <h1>{data.name}</h1>
      <p className="muted">{data.short_description}</p>

      {data.images.length > 0 && (
        <div className="grid cols-3" style={{ marginBottom: 20 }}>
          {data.images.map((img) => (
            <img key={img.id} src={mediaUrl(`/api/v1/media/public/${img.file_path.replace(/^public\//, "")}`)} alt={img.alt_text || ""}
                 style={{ width: "100%", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }} />
          ))}
        </div>
      )}
      <div className="grid cols-2">
        <div className="panel">
          <h2>Product information</h2>
          <p>{data.full_description}</p>
          {data.benefits && <><h3>Benefits</h3><p>{data.benefits}</p></>}
          {data.recommended_crops && <p><strong>Recommended crops:</strong> {data.recommended_crops}</p>}
          {data.dosage_value && <p><strong>Dosage:</strong> {data.dosage_value} {data.dosage_unit}</p>}
          {data.precautions && <><h3>Precautions</h3><p>{data.precautions}</p></>}
        </div>

        <div className="panel">
          <h2>Reviews</h2>
          <p className="small muted">
            {data.approved_review_count > 0
              ? `${data.average_rating?.toFixed(1)} average from ${data.approved_review_count} approved review(s).`
              : "No approved reviews yet."}
          </p>
          <ul className="stack" style={{ listStyle: "none", padding: 0 }}>
            {data.reviews.map((r) => (
              <li key={r.id} className="panel">
                <strong>{r.reviewer_name}</strong> — {r.rating}/5
                {r.comment && <p className="small">{r.comment}</p>}
              </li>
            ))}
          </ul>

          <h3>Submit a review</h3>
          {submitted ? (
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
                <label htmlFor="reviewer_name">Your name</label>
                <input id="reviewer_name" required value={form.reviewer_name} onChange={(e) => setForm({ ...form, reviewer_name: e.target.value })} />
              </div>
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
                {submitReview.isPending ? "Submitting..." : "Submit review"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
