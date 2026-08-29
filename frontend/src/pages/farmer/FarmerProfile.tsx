import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../api/client";

interface FarmerProfileOut {
  id: string; state: string; district: string | null; mandal: string | null; village: string | null;
  pin_code: string | null; farm_size: number | null; farm_size_unit: string | null; main_crops: string | null;
  irrigation_type: string | null; preferred_language: string; preferred_contact_method: string; public_data_opt_in: boolean;
}

const IRRIGATION_TYPES = ["rainfed", "borewell", "canal", "drip", "sprinkler", "tank", "other"];
const LANGUAGES: [string, string][] = [["en", "English"], ["te", "Telugu"], ["hi", "Hindi"]];
const CONTACT_METHODS = ["phone", "sms", "whatsapp", "email"];

export function FarmerProfile() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["farmer-profile"], queryFn: () => api.get<FarmerProfileOut>("/farmers/me/profile") });
  const [form, setForm] = useState<Partial<FarmerProfileOut>>({});
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const update = useMutation({
    mutationFn: () => api.put<FarmerProfileOut>("/farmers/me/profile", form),
    onSuccess: () => {
      setSaved(true);
      setError(null);
      qc.invalidateQueries({ queryKey: ["farmer-profile"] });
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  if (isLoading || !data) return <div className="loading-state">Loading your profile...</div>;

  return (
    <div>
      <h2>My profile</h2>
      <p className="muted">This farm information helps staff match you with the right dealers and field officers.</p>
      {saved && <div className="alert alert-success">Profile updated.</div>}
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={(e) => { e.preventDefault(); update.mutate(); }} className="panel">
        <div className="grid cols-2">
          <div className="field"><label htmlFor="state">State</label>
            <input type="text" id="state" value={form.state || ""} onChange={(e) => setForm({ ...form, state: e.target.value })} /></div>
          <div className="field"><label htmlFor="district">District</label>
            <input type="text" id="district" value={form.district || ""} onChange={(e) => setForm({ ...form, district: e.target.value })} /></div>
          <div className="field"><label htmlFor="mandal">Mandal</label>
            <input type="text" id="mandal" value={form.mandal || ""} onChange={(e) => setForm({ ...form, mandal: e.target.value })} /></div>
          <div className="field"><label htmlFor="village">Village</label>
            <input type="text" id="village" value={form.village || ""} onChange={(e) => setForm({ ...form, village: e.target.value })} /></div>
          <div className="field"><label htmlFor="pin_code">PIN code</label>
            <input type="text" id="pin_code" value={form.pin_code || ""} onChange={(e) => setForm({ ...form, pin_code: e.target.value })} /></div>
          <div className="field"><label htmlFor="farm_size">Farm size</label>
            <input type="number" step="0.1" id="farm_size" value={form.farm_size ?? ""} onChange={(e) => setForm({ ...form, farm_size: e.target.value ? Number(e.target.value) : null })} /></div>
          <div className="field"><label htmlFor="farm_size_unit">Farm size unit</label>
            <input type="text" id="farm_size_unit" placeholder="acres, hectares..." value={form.farm_size_unit || ""} onChange={(e) => setForm({ ...form, farm_size_unit: e.target.value })} /></div>
          <div className="field"><label htmlFor="main_crops">Main crops</label>
            <input type="text" id="main_crops" placeholder="e.g. Paddy, Cotton" value={form.main_crops || ""} onChange={(e) => setForm({ ...form, main_crops: e.target.value })} /></div>
          <div className="field"><label htmlFor="irrigation_type">Irrigation type</label>
            <select id="irrigation_type" value={form.irrigation_type || ""} onChange={(e) => setForm({ ...form, irrigation_type: e.target.value })}>
              <option value="">Not specified</option>
              {IRRIGATION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select></div>
          <div className="field"><label htmlFor="preferred_language">Preferred language</label>
            <select id="preferred_language" value={form.preferred_language || "en"} onChange={(e) => setForm({ ...form, preferred_language: e.target.value })}>
              {LANGUAGES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
            </select></div>
          <div className="field"><label htmlFor="preferred_contact_method">Preferred contact method</label>
            <select id="preferred_contact_method" value={form.preferred_contact_method || "phone"} onChange={(e) => setForm({ ...form, preferred_contact_method: e.target.value })}>
              {CONTACT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select></div>
        </div>
        <label><input type="checkbox" checked={form.public_data_opt_in ?? false}
          onChange={(e) => setForm({ ...form, public_data_opt_in: e.target.checked })} /> Allow anonymized, aggregated data from my profile to be used in public farming insights</label>
        <div style={{ marginTop: 16 }}>
          <button className="btn btn-primary" type="submit" disabled={update.isPending}>Save profile</button>
        </div>
      </form>
    </div>
  );
}
