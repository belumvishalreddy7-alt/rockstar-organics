import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api, uploadFile } from "../../api/client";
import { StatusBadge } from "../../components/StatusBadge";

interface TimelineEntry { id: string; body: string; is_private: boolean; event_type: string; created_at: string; }
interface CaseOut { id: string; reference_number: string; title: string; description: string; status: string; timeline: TimelineEntry[]; }

export function CaseDetail() {
  const { caseId } = useParams();
  const qc = useQueryClient();
  const [message, setMessage] = useState("");

  const { data, isLoading } = useQuery({ queryKey: ["case", caseId], queryFn: () => api.get<CaseOut>(`/cases/${caseId}`) });

  const sendMessage = useMutation({
    mutationFn: () => api.post(`/cases/${caseId}/messages`, { body: message, is_private: false }),
    onSuccess: () => {
      setMessage("");
      qc.invalidateQueries({ queryKey: ["case", caseId] });
    },
  });

  const [uploadError, setUploadError] = useState<string | null>(null);
  const uploadAttachment = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return uploadFile(`/media/cases/${caseId}/attachments`, formData);
    },
    onSuccess: () => {
      setUploadError(null);
      qc.invalidateQueries({ queryKey: ["case", caseId] });
    },
    onError: (e: unknown) => setUploadError(e instanceof Error ? e.message : "Upload failed."),
  });

  if (isLoading || !data) return <div className="loading-state">Loading case...</div>;

  return (
    <div className="panel">
      <div className="inline">
        <h2>{data.title}</h2>
        <StatusBadge status={data.status} />
      </div>
      <p className="muted">Reference: {data.reference_number}</p>
      <p>{data.description}</p>

      <h3>Timeline</h3>
      <ul className="timeline">
        {data.timeline.map((t) => (
          <li key={t.id}>
            <p>{t.body}</p>
            <p className="meta">{new Date(t.created_at).toLocaleString()} · {t.event_type.replace("_", " ")}</p>
          </li>
        ))}
      </ul>

      <h3>Attach a photo or document</h3>
      {uploadError && <div className="alert alert-error">{uploadError}</div>}
      <div className="field">
        <label htmlFor="attachment">Photo (JPEG/PNG/WebP) or PDF, up to 10MB</label>
        <input
          id="attachment"
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) uploadAttachment.mutate(file);
            e.target.value = "";
          }}
        />
      </div>

      <h3>Add a message</h3>
      <form onSubmit={(e) => { e.preventDefault(); sendMessage.mutate(); }}>
        <div className="field">
          <label htmlFor="message">Message</label>
          <textarea id="message" required value={message} onChange={(e) => setMessage(e.target.value)} />
        </div>
        <button className="btn btn-primary" type="submit" disabled={sendMessage.isPending}>Send</button>
      </form>
    </div>
  );
}
