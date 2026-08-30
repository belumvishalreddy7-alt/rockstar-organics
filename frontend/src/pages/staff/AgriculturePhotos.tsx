import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, ApiError, uploadFile, fetchAuthedImageUrl } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface PhotoRow {
  id: string; title: string; category: string; status: string; usage_rights_verified: boolean;
  rejection_reason: string | null; image_url: string; admin_image_url: string;
}

/** The photo's own file isn't public until it's published, so the thumbnail
 * is fetched with the session cookie and shown as a local object URL. */
function PhotoThumbnail({ photo }: { photo: PhotoRow }) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchAuthedImageUrl(photo.admin_image_url).then((url) => {
      if (cancelled) { URL.revokeObjectURL(url); return; }
      objectUrl = url;
      setSrc(url);
    }).catch(() => setSrc(null));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [photo.admin_image_url]);

  if (!src) return <div style={{ width: 60, height: 40, background: "#eee", borderRadius: 4 }} />;
  return <img src={src} alt={photo.title} style={{ width: 60, height: 40, objectFit: "cover", borderRadius: 4 }} />;
}

const CATEGORIES = [
  "farmers", "farms", "fields", "crops", "product_application", "dealer_network",
  "distributor_network", "field_visits", "agricultural_activities",
  "company_facilities", "manufacturing", "research", "community_activities",
];

export function AgriculturePhotos() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [altText, setAltText] = useState("");
  const [location, setLocation] = useState("");
  const [crop, setCrop] = useState("");
  const [photographerSource, setPhotographerSource] = useState("");
  const [usageRightsVerified, setUsageRightsVerified] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({ queryKey: ["agriculture-photos-admin"], queryFn: () => api.get<PhotoRow[]>("/media/agriculture/admin") });

  const create = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose an image first.");
      const formData = new FormData();
      formData.append("file", file);
      const uploaded = await uploadFile<{ id: string }>("/media/agriculture-photos", formData);
      return api.post("/media/agriculture", {
        title, category, alt_text: altText, media_id: uploaded.id,
        location: location || undefined, crop: crop || undefined,
        photographer_source: photographerSource || undefined, usage_rights_verified: usageRightsVerified,
      });
    },
    onSuccess: () => {
      setTitle(""); setAltText(""); setLocation(""); setCrop(""); setPhotographerSource(""); setFile(null); setUsageRightsVerified(false);
      setMessage("Photo uploaded as a draft. Approve and publish it once usage rights are verified.");
      qc.invalidateQueries({ queryKey: ["agriculture-photos-admin"] });
    },
    onError: (e: unknown) => setMessage(e instanceof Error ? e.message : "Upload failed."),
  });

  const [actionError, setActionError] = useState<string | null>(null);

  const changeStatus = useMutation({
    mutationFn: ({ id, status, rejection_reason }: { id: string; status: string; rejection_reason?: string }) =>
      api.post(`/media/agriculture/${id}/status/${status}`, rejection_reason ? { rejection_reason } : {}),
    onSuccess: () => { setActionError(null); qc.invalidateQueries({ queryKey: ["agriculture-photos-admin"] }); },
    onError: (e: unknown) => setActionError(e instanceof ApiError ? e.message : "Action failed."),
  });

  const removePhoto = useMutation({
    mutationFn: (id: string) => api.del(`/media/agriculture/${id}`),
    onSuccess: () => { setActionError(null); qc.invalidateQueries({ queryKey: ["agriculture-photos-admin"] }); },
    onError: (e: unknown) => setActionError(e instanceof ApiError ? e.message : "Could not remove this photo."),
  });

  return (
    <div>
      <h2>Agriculture photo gallery</h2>
      <div className="panel" style={{ marginBottom: 16 }}>
        <h3>Upload a photo</h3>
        {message && <p className="small">{message}</p>}
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <div className="field"><label htmlFor="photo-title">Title</label>
            <input type="text" id="photo-title" required value={title} onChange={(e) => setTitle(e.target.value)} /></div>
          <div className="field"><label htmlFor="photo-category">Category</label>
            <select id="photo-category" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div className="field"><label htmlFor="photo-alt">Alt text (accurate, accessible description)</label>
            <input type="text" id="photo-alt" required value={altText} onChange={(e) => setAltText(e.target.value)} /></div>
          <div className="field"><label htmlFor="photo-location">Location (leave blank if unverified)</label>
            <input type="text" id="photo-location" value={location} onChange={(e) => setLocation(e.target.value)} /></div>
          <div className="field"><label htmlFor="photo-crop">Crop (leave blank if unverified)</label>
            <input type="text" id="photo-crop" value={crop} onChange={(e) => setCrop(e.target.value)} /></div>
          <div className="field"><label htmlFor="photo-source">Photographer/source (leave blank if unverified)</label>
            <input type="text" id="photo-source" value={photographerSource} onChange={(e) => setPhotographerSource(e.target.value)} /></div>
          <div className="field">
            <label><input type="checkbox" checked={usageRightsVerified} onChange={(e) => setUsageRightsVerified(e.target.checked)} /> Usage rights verified (owned by or licensed to Rockstar Organics)</label>
          </div>
          <div className="field"><label htmlFor="photo-file">Image (JPG, PNG, WebP)</label>
            <input id="photo-file" type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setFile(e.target.files?.[0] || null)} /></div>
          <button className="btn btn-primary" type="submit" disabled={create.isPending}>
            {create.isPending ? "Uploading..." : "Upload"}
          </button>
        </form>
      </div>

      {actionError && <div className="alert alert-error">{actionError}</div>}
      {isLoading && <div className="loading-state">Loading photos...</div>}
      {data && data.length === 0 && <EmptyState title="No photos uploaded yet." />}
      {data && data.length > 0 && (
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th>Photo</th><th>Title</th><th>Category</th><th>Status</th><th>Rights verified</th><th>Actions</th></tr></thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.id}>
                  <td><PhotoThumbnail photo={p} /></td>
                  <td>
                    {p.title}
                    {p.rejection_reason && <p className="small muted">Rejected: {p.rejection_reason}</p>}
                  </td>
                  <td>{p.category.replace(/_/g, " ")}</td>
                  <td><StatusBadge status={p.status} /></td>
                  <td>{p.usage_rights_verified ? "Yes" : "No"}</td>
                  <td className="inline">
                    {p.status !== "under_review" && p.status !== "published" && (
                      <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: p.id, status: "under_review" })}>Under review</button>
                    )}
                    {p.status !== "approved" && p.status !== "published" && (
                      <button className="btn btn-primary btn-sm" onClick={() => changeStatus.mutate({ id: p.id, status: "approved" })}>Approve</button>
                    )}
                    {p.status !== "rejected" && p.status !== "published" && (
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => {
                          const reason = window.prompt("Reason for rejecting this photo:") || "";
                          changeStatus.mutate({ id: p.id, status: "rejected", rejection_reason: reason });
                        }}
                      >
                        Reject
                      </button>
                    )}
                    {p.status === "approved" && (
                      <button className="btn btn-primary btn-sm" onClick={() => changeStatus.mutate({ id: p.id, status: "published" })}>Publish</button>
                    )}
                    {p.status !== "archived" && <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: p.id, status: "archived" })}>Archive</button>}
                    {p.status === "archived" && <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: p.id, status: "draft" })}>Restore to draft</button>}
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => {
                        if (window.confirm(`Permanently remove "${p.title}"? This cannot be undone.`)) removePhoto.mutate(p.id);
                      }}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
