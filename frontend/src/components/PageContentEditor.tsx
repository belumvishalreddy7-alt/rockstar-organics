import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { WorkflowActions } from "./WorkflowActions";

interface PageContentOut {
  id: string; section: string; status: string; fields: Record<string, string>;
}

interface PageContentEditorProps {
  section: string;
  fieldKeys: { key: string; label: string }[];
  userRole: string;
}

/** Editor for one corporate page section's free-text overview fields
 * (e.g. Manufacturing's "capabilities"/"processes"/...). Goes through the
 * same verify/approve/publish workflow as every structured record, so
 * overview copy can't reach the live site without review either. */
export function PageContentEditor({ section, fieldKeys, userRole }: PageContentEditorProps) {
  const qc = useQueryClient();
  const queryKey = ["company-page-content-admin", section];
  const [form, setForm] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({ queryKey, queryFn: () => api.get<PageContentOut>(`/company/pages/admin/${section}`) });

  useEffect(() => {
    if (data) setForm(Object.fromEntries(fieldKeys.map((f) => [f.key, data.fields[f.key] || ""])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.id]);

  const save = useMutation({
    mutationFn: () => api.put(`/company/pages/admin/${section}`, { fields: form, source_reference: null }),
    onSuccess: () => { setError(null); qc.invalidateQueries({ queryKey }); },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Could not save."),
  });

  if (isLoading || !data) return <div className="loading-state">Loading overview content...</div>;

  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <h3>Overview content</h3>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        {fieldKeys.map((f) => (
          <div className="field" key={f.key}>
            <label htmlFor={`overview-${section}-${f.key}`}>{f.label}</label>
            <textarea id={`overview-${section}-${f.key}`} value={form[f.key] ?? ""} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
          </div>
        ))}
        <button className="btn btn-primary btn-sm" type="submit" disabled={save.isPending}>Save overview</button>
      </form>
      <div style={{ marginTop: 12 }}>
        <WorkflowActions basePath="/company/pages" itemId={data.id} status={data.status} userRole={userRole} queryKey={queryKey} onError={setError} />
      </div>
    </div>
  );
}
