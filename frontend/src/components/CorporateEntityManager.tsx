import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
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

interface CorporateEntityManagerProps {
  title: string;
  basePath: string;
  labelField: string;
  subLabelField?: string;
  fields: FieldConfig[];
  userRole: string;
}

export function CorporateEntityManager({ title, basePath, labelField, subLabelField, fields, userRole }: CorporateEntityManagerProps) {
  const qc = useQueryClient();
  const queryKey = ["corporate-admin", basePath];
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, string>>(emptyForm(fields));
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({ queryKey, queryFn: () => api.get<Item[]>(`${basePath}/admin`) });

  const create = useMutation({
    mutationFn: () => api.post(basePath, toPayload(fields, form)),
    onSuccess: () => { setShowForm(false); setForm(emptyForm(fields)); setError(null); qc.invalidateQueries({ queryKey }); },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const update = useMutation({
    mutationFn: (id: string) => api.put(`${basePath}/${id}`, toPayload(fields, form)),
    onSuccess: () => { setEditingId(null); setForm(emptyForm(fields)); setError(null); qc.invalidateQueries({ queryKey }); },
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
          <button className="btn btn-primary btn-sm" onClick={() => { setShowForm(true); setForm(emptyForm(fields)); }}>Add</button>
        )}
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      {(showForm || editingId) && (
        <form
          onSubmit={(e) => { e.preventDefault(); editingId ? update.mutate(editingId) : create.mutate(); }}
          style={{ marginBottom: 16, borderBottom: "1px solid var(--color-border)", paddingBottom: 16 }}
        >
          {fields.map(renderField)}
          <div className="inline">
            <button className="btn btn-primary btn-sm" type="submit" disabled={create.isPending || update.isPending}>
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
