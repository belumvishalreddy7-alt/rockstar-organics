import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, uploadFile } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface DocRow {
  id: string; title: string; document_type: string; verification_status: string; is_published: boolean;
  reference_number: string | null;
}

const DOCUMENT_TYPES = [
  "company_certificate", "registration_document", "manufacturing_certificate", "quality_certificate",
  "compliance_document", "licence", "product_certificate", "other",
];

export function CompanyDocuments() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0]);
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({ queryKey: ["company-documents-admin"], queryFn: () => api.get<DocRow[]>("/company/documents/admin") });

  const create = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a file first.");
      const formData = new FormData();
      formData.append("file", file);
      const uploaded = await uploadFile<{ id: string }>("/media/company-documents", formData);
      return api.post("/company/documents", { title, document_type: documentType, media_id: uploaded.id });
    },
    onSuccess: () => {
      setTitle("");
      setFile(null);
      setMessage("Document uploaded. Verify it before publishing.");
      qc.invalidateQueries({ queryKey: ["company-documents-admin"] });
    },
    onError: (e: unknown) => setMessage(e instanceof Error ? e.message : "Upload failed."),
  });

  const verify = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/company/documents/${id}/verify/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["company-documents-admin"] }),
  });

  const publish = useMutation({
    mutationFn: ({ id, publish }: { id: string; publish: boolean }) =>
      api.post(`/company/documents/${id}/${publish ? "publish" : "unpublish"}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["company-documents-admin"] }),
  });

  return (
    <div>
      <h2>Company certificates &amp; documents</h2>
      <div className="panel" style={{ marginBottom: 16 }}>
        <h3>Upload a document</h3>
        {message && <p className="small">{message}</p>}
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <div className="field"><label htmlFor="doc-title">Title</label>
            <input id="doc-title" required value={title} onChange={(e) => setTitle(e.target.value)} /></div>
          <div className="field"><label htmlFor="doc-type">Document type</label>
            <select id="doc-type" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
              {DOCUMENT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div className="field"><label htmlFor="doc-file">File (PDF, JPG, PNG, WebP)</label>
            <input id="doc-file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf"
                   onChange={(e) => setFile(e.target.files?.[0] || null)} /></div>
          <button className="btn btn-primary" type="submit" disabled={create.isPending}>
            {create.isPending ? "Uploading..." : "Upload"}
          </button>
        </form>
      </div>

      {isLoading && <div className="loading-state">Loading documents...</div>}
      {data && data.length === 0 && <EmptyState title="No documents uploaded yet." />}
      {data && data.length > 0 && (
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th>Title</th><th>Type</th><th>Verification</th><th>Published</th><th>Actions</th></tr></thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.id}>
                  <td>{d.title}</td><td>{d.document_type.replace(/_/g, " ")}</td>
                  <td><StatusBadge status={d.verification_status} /></td>
                  <td>{d.is_published ? "Yes" : "No"}</td>
                  <td className="inline">
                    {d.verification_status !== "verified" && (
                      <button className="btn btn-primary btn-sm" onClick={() => verify.mutate({ id: d.id, status: "verified" })}>Verify</button>
                    )}
                    {d.verification_status !== "rejected" && (
                      <button className="btn btn-ghost btn-sm" onClick={() => verify.mutate({ id: d.id, status: "rejected" })}>Reject</button>
                    )}
                    {d.verification_status === "verified" && !d.is_published && (
                      <button className="btn btn-primary btn-sm" onClick={() => publish.mutate({ id: d.id, publish: true })}>Publish</button>
                    )}
                    {d.is_published && (
                      <button className="btn btn-ghost btn-sm" onClick={() => publish.mutate({ id: d.id, publish: false })}>Unpublish</button>
                    )}
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
