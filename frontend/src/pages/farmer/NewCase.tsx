import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../../api/client";

export function NewCase() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "", description: "", crop: "", crop_stage: "", district: "", mandal: "", village: "", severity: "medium",
  });
  const [error, setError] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: () => api.post<{ id: string; reference_number: string }>("/cases", form),
    onSuccess: (r) => navigate(`/farmer/cases/${r.id}`),
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  return (
    <div className="panel">
      <h2>Submit a support request</h2>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
        <div className="field"><label htmlFor="title">Title</label>
          <input id="title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
        <div className="field"><label htmlFor="description">Describe the issue</label>
          <textarea id="description" required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
        <div className="field"><label htmlFor="crop">Crop</label>
          <input id="crop" value={form.crop} onChange={(e) => setForm({ ...form, crop: e.target.value })} /></div>
        <div className="field"><label htmlFor="district">District</label>
          <input id="district" required value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></div>
        <div className="field"><label htmlFor="mandal">Mandal</label>
          <input id="mandal" value={form.mandal} onChange={(e) => setForm({ ...form, mandal: e.target.value })} /></div>
        <div className="field"><label htmlFor="severity">Severity</label>
          <select id="severity" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
            <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option>
          </select></div>
        <button className="btn btn-primary" type="submit" disabled={submit.isPending}>{submit.isPending ? "Submitting..." : "Submit case"}</button>
      </form>
    </div>
  );
}
