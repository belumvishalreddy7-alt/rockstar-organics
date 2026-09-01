import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, mediaUrl, uploadFile } from "../api/client";
import { EmptyState } from "./EmptyState";
import { WorkflowActions } from "./WorkflowActions";

export interface FieldConfig {
  key: string;
  label: string;
  type: "text" | "textarea" | "date" | "number" | "url";
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Item = Record<string, any>;

function emptyForm(fields: FieldConfig[]): Record<string, string> {
  return Object.fromEntries(fields.map((f) => [f.key, ""]));
}

function toPayload(fields: FieldConfig[], form: Record<string, string>): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const f of fields) {
    const raw = form[f.key];
    if (f.type === "number") payload[f.key] = raw === "" ? 0 : Number(raw);
    else payload[f.key] = raw === "" ? null : raw;
  }
  return payload;
}

function formFromItem(fields: FieldConfig[], item: Item): Record<string, string> {
  const form: Record<string, string> = {};
  for (const f of fields) {
    const value = item[f.key];
    form[f.key] = f.type === "date" && value ? String(value).slice(0, 10) : value == null ? "" : String(value);
  }
  return form;
}

export interface MediaConfig {
  /** Payload key holding the uploaded media's id, e.g. "photo_media_id". */
  field: string;
  /** Matching output key holding the resolved public URL, e.g. "photo_url". */
  urlField: string;
  /** Purpose passed to POST /media/corporate/{purpose} - must be one of
   * CORPORATE_MEDIA_PURPOSES on the backend. */
  purpose: string;
  label: string;
  accept: string;
}

interface CorporateEntityManagerProps {
  title: string;
  basePath: string;
  labelField: string;
  subLabelField?: string;
  fields: FieldConfig[];
  userRole: string;
  media?: MediaConfig;
}

export function CorporateEntityManager({ title, basePath, labelField, subLabelField, fields, userRole, media }: CorporateEntityManagerProps) {
  const qc = useQueryClient();
  const queryKey = ["corporate-admin", basePath];
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, string>>(emptyForm(fields));
  const [mediaId, setMediaId] = useState<string | null>(null);
  const [mediaUploading, setMediaUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({ queryKey, queryFn: () => api.get<Item[]>(`${basePath}/admin`) });

  const uploadMedia = async (file: File) => {
    if (!media) return;
    setMediaUploading(true);
    try {
      const uploaded = await uploadFile<{ id: string }>(`/media/corporate/${media.purpose}`, (() => {
        const fd = new FormData();
        fd.append("file", file);
        return fd;
      })());
      setMediaId(uploaded.id);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not upload that file.");
    } finally {
      setMediaUploading(false);
    }
  };

  const withMedia = (payload: Record<string, unknown>) => (media ? { ...payload, [media.field]: mediaId } : payload);

  const create = useMutation({
    mutationFn: () => api.post(basePath, withMedia(toPayload(fields, form))),
    onSuccess: () => { setShowForm(false); setForm(emptyForm(fields)); setMediaId(null); setError(null); qc.invalidateQueries({ queryKey }); },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const update = useMutation({
    mutationFn: (id: string) => api.put(`${basePath}/${id}`, withMedia(toPayload(fields, form))),
    onSuccess: () => { setEditingId(null); setForm(emptyForm(fields)); setMediaId(null); setError(null); qc.invalidateQueries({ queryKey }); },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del(`${basePath}/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey }),
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Could not delete."),
  });

  const startEdit = (item: Item) => {
    setEditingId(item.id);
    setForm(formFromItem(fields, item));
    setMediaId(media ? (item[media.field] ?? null) : null);
    setShowForm(false);
    setError(null);
  };

  const renderField = (f: FieldConfig) => (
    <div className="field" key={f.key}>
      <label htmlFor={`${basePath}-${f.key}`}>{f.label}</label>
      {f.type === "textarea" ? (
        <textarea id={`${basePath}-${f.key}`} value={form[f.key] ?? ""} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
      ) : (
        <input
          id={`${basePath}-${f.key}`}
          type={f.type === "date" ? "date" : f.type === "number" ? "number" : f.type === "url" ? "text" : "text"}
          value={form[f.key] ?? ""}
          onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
        />
      )}
    </div>
  );

  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <div className="section-heading">
        <h3>{title}</h3>
        {!showForm && !editingId && (
          <button className="btn btn-primary btn-sm" onClick={() => { setShowForm(true); setForm(emptyForm(fields)); setMediaId(null); }}>Add</button>
        )}
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      {(showForm || editingId) && (
        <form
          onSubmit={(e) => { e.preventDefault(); editingId ? update.mutate(editingId) : create.mutate(); }}
          style={{ marginBottom: 16, borderBottom: "1px solid var(--color-border)", paddingBottom: 16 }}
        >
          {fields.map(renderField)}
          {media && (
            <div className="field">
              <label htmlFor={`${basePath}-media`}>{media.label}</label>
              {mediaId && <p className="small muted">Uploaded - choose a different file to replace it.</p>}
              <input
                id={`${basePath}-media`} type="file" accept={media.accept}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadMedia(f); }}
              />
              {mediaUploading && <p className="small muted">Uploading...</p>}
            </div>
          )}
          <div className="inline">
            <button className="btn btn-primary btn-sm" type="submit" disabled={create.isPending || update.isPending || mediaUploading}>
              {editingId ? "Save changes" : "Create draft"}
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setShowForm(false); setEditingId(null); }}>Cancel</button>
          </div>
        </form>
      )}

      {isLoading && <div className="loading-state">Loading...</div>}
      {data && data.length === 0 && <EmptyState title="Nothing added yet." />}
      <div className="stack">
        {data?.map((item) => (
          <div key={item.id} className="panel">
            <div className="section-heading">
              <div>
                <strong>{item[labelField] || "(untitled)"}</strong>
                {subLabelField && item[subLabelField] && <div className="small muted">{item[subLabelField]}</div>}
                {media && item[media.urlField] && (
                  media.accept.includes("pdf") ? (
                    <div className="small"><a href={mediaUrl(item[media.urlField])} target="_blank" rel="noreferrer">View {media.label.toLowerCase()}</a></div>
                  ) : (
                    <img src={mediaUrl(item[media.urlField])} alt="" style={{ width: 80, height: 60, objectFit: "cover", borderRadius: 4, marginTop: 6 }} />
                  )
                )}
              </div>
              <div className="inline">
                <button className="btn btn-ghost btn-sm" onClick={() => startEdit(item)}>Edit</button>
                {item.status === "draft" && (
                  <button className="btn btn-danger btn-sm" onClick={() => { if (window.confirm("Permanently delete this draft?")) remove.mutate(item.id); }}>
                    Delete
                  </button>
                )}
              </div>
            </div>
            <WorkflowActions basePath={basePath} itemId={item.id} status={item.status} userRole={userRole} queryKey={queryKey} onError={setError} />
          </div>
        ))}
      </div>
    </div>
  );
}
