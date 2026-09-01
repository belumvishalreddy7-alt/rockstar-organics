/**
 * Dedicated corporate pages (Leadership, Manufacturing, R&D, Quality &
 * Safety, Sustainability, Farmer Stories, Careers).
 *
 * The five CMS-backed sections (everything except Farmer Stories/Careers)
 * are real, database-driven pages: they fetch the section's overview text
 * from /api/v1/company/pages/public/{section} and its structured records
 * (profiles/facilities/certifications/initiatives) from each domain's own
 * /public endpoint. Nothing is invented here - a section with no published
 * content yet falls back to "Information pending verification." exactly
 * as the backend leaves it, and an owner/manager adds real content through
 * the CMS in Staff -> Corporate content without any change to this page.
 */
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError, mediaUrl } from "../../api/client";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";

const PENDING = "Information pending verification.";

interface PageContentOut { section: string; fields: Record<string, string>; }

function fieldLabel(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function useSectionOverview(section: string) {
  return useQuery({
    queryKey: ["company-page-content", section],
    queryFn: async () => {
      try {
        return await api.get<PageContentOut>(`/company/pages/public/${section}`);
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
  });
}

function OverviewPanel({ section, fallback }: { section: string; fallback: string }) {
  const { data, isLoading } = useSectionOverview(section);
  if (isLoading) return <div className="loading-state">Loading...</div>;
  const entries = data ? Object.entries(data.fields).filter(([, v]) => v && v.trim()) : [];
  if (entries.length === 0) {
    return (
      <div className="panel">
        <p className="small muted">{fallback}</p>
      </div>
    );
  }
  return (
    <div className="panel">
      {entries.map(([key, value]) => (
        <div key={key} style={{ marginBottom: 16 }}>
          <h3>{fieldLabel(key)}</h3>
          <p className="muted" style={{ whiteSpace: "pre-line" }}>{value}</p>
        </div>
      ))}
    </div>
  );
}

function Hero({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <>
      <h1>{title}</h1>
      <p className="muted" style={{ maxWidth: 640 }}>{subtitle}</p>
    </>
  );
}

// --- Leadership -------------------------------------------------------

interface LeadershipProfileOut {
  id: string; full_name: string; position: string; biography: string | null;
  responsibilities: string | null; experience: string | null; education: string | null;
  profile_url: string | null; joining_date: string | null; photo_url: string | null;
}

export function Leadership() {
  const { data, isLoading } = useQuery({
    queryKey: ["leadership-public"],
    queryFn: () => api.get<LeadershipProfileOut[]>("/leadership/public"),
  });

  return (
    <div className="container page-section">
      <Hero title="Leadership" subtitle="Information about the leadership and management team of Rockstar Organics." />
      <OverviewPanel section="leadership" fallback={PENDING} />
      <div style={{ marginTop: 24 }}>
        {isLoading && <div className="loading-state">Loading...</div>}
        {data && data.length === 0 && <p className="small muted">Leadership information pending verification.</p>}
        {data && data.length > 0 && (
          <div className="grid cols-3">
            {data.map((p) => (
              <Link key={p.id} to={`/leadership/${p.id}`} className="panel" style={{ display: "block", textDecoration: "none" }}>
                {p.photo_url && <img src={mediaUrl(p.photo_url)} alt="" style={{ width: "100%", aspectRatio: "1", objectFit: "cover", borderRadius: "var(--radius-md)", marginBottom: 8 }} />}
                <h3>{p.full_name}</h3>
                <p className="small muted">{p.position}</p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function LeadershipDetail() {
  const { id } = useParams();
  const { data, isLoading } = useQuery({
    queryKey: ["leadership-detail", id],
    queryFn: () => api.get<LeadershipProfileOut>(`/leadership/public/${id}`),
  });
  useDocumentTitle(data ? `${data.full_name} | Rockstar Organics` : "Leadership | Rockstar Organics");

  if (isLoading) return <div className="container page-section"><div className="loading-state">Loading...</div></div>;
  if (!data) return <div className="container page-section"><p className="small muted">Leadership information pending verification.</p></div>;

  return (
    <div className="container page-section">
      <p className="small"><Link to="/leadership">&larr; Leadership</Link></p>
      <h1>{data.full_name}</h1>
      <p className="muted">{data.position}</p>
      <div className="panel">
        {data.photo_url && <img src={mediaUrl(data.photo_url)} alt={data.full_name} style={{ width: 160, height: 160, objectFit: "cover", borderRadius: "var(--radius-md)", marginBottom: 16 }} />}
        <h3>Biography</h3>
        <p className="muted">{data.biography || PENDING}</p>
        <h3>Responsibilities</h3>
        <p className="muted">{data.responsibilities || PENDING}</p>
        <h3>Professional background</h3>
        <p className="muted">{data.experience || PENDING}</p>
        <h3>Education</h3>
        <p className="muted">{data.education || PENDING}</p>
        {data.profile_url && <p className="small"><a href={data.profile_url} target="_blank" rel="noreferrer">Official profile</a></p>}
      </div>
    </div>
  );
}

// --- Manufacturing ------------------------------------------------------

interface FacilityOut {
  id: string; name: string; facility_type: string | null; address: string | null;
  description: string | null; capabilities: string | null; capacity: string | null; photo_url: string | null;
}

export function Manufacturing() {
  const { data, isLoading } = useQuery({
    queryKey: ["manufacturing-facilities-public"],
    queryFn: () => api.get<FacilityOut[]>("/manufacturing/facilities/public"),
  });

  return (
    <div className="container page-section">
      <Hero title="Manufacturing" subtitle="Information about Rockstar Organics manufacturing capabilities, facilities and processes." />
      <OverviewPanel section="manufacturing" fallback="Manufacturing information pending verification." />
      <div style={{ marginTop: 24 }}>
        <h2>Facilities</h2>
        {isLoading && <div className="loading-state">Loading...</div>}
        {data && data.length === 0 && <p className="small muted">Manufacturing photographs pending verification.</p>}
        {data && data.length > 0 && (
          <div className="grid cols-2">
            {data.map((f) => (
              <div className="panel" key={f.id}>
                {f.photo_url && <img src={mediaUrl(f.photo_url)} alt="" style={{ width: "100%", aspectRatio: "16/9", objectFit: "cover", borderRadius: "var(--radius-md)", marginBottom: 8 }} />}
                <h3>{f.name}</h3>
                {f.facility_type && <p className="small muted">{f.facility_type}</p>}
                <p className="small muted">{f.description || PENDING}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- Research & Development ----------------------------------------------

interface ResearchAreaOut { id: string; title: string; description: string | null; image_url: string | null; }

export function ResearchAndDevelopment() {
  const facilities = useQuery({
    queryKey: ["research-facilities-public"],
    queryFn: () => api.get<FacilityOut[]>("/research/facilities/public"),
  });
  const areas = useQuery({
    queryKey: ["research-areas-public"],
    queryFn: () => api.get<ResearchAreaOut[]>("/research/areas/public"),
  });

  return (
    <div className="container page-section">
      <Hero title="Research & Development" subtitle="Information about Rockstar Organics research, development and innovation activities." />
      <OverviewPanel section="research_development" fallback="Research & Development information pending verification." />

      <div style={{ marginTop: 24 }}>
        <h2>Research areas</h2>
        {areas.data && areas.data.length === 0 && <p className="small muted">Information pending verification.</p>}
        {areas.data && areas.data.length > 0 && (
          <div className="grid cols-3">
            {areas.data.map((a) => (
              <div className="panel" key={a.id}>
                {a.image_url && <img src={mediaUrl(a.image_url)} alt="" style={{ width: "100%", aspectRatio: "4/3", objectFit: "cover", borderRadius: "var(--radius-md)", marginBottom: 8 }} />}
                <h3>{a.title}</h3>
                <p className="small muted">{a.description || PENDING}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: 24 }}>
        <h2>Research facilities</h2>
        {facilities.data && facilities.data.length === 0 && <p className="small muted">Information pending verification.</p>}
        {facilities.data && facilities.data.length > 0 && (
          <div className="grid cols-2">
            {facilities.data.map((f) => (
              <div className="panel" key={f.id}>
                {f.photo_url && <img src={mediaUrl(f.photo_url)} alt="" style={{ width: "100%", aspectRatio: "16/9", objectFit: "cover", borderRadius: "var(--radius-md)", marginBottom: 8 }} />}
                <h3>{f.name}</h3>
                <p className="small muted">{f.description || PENDING}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- Quality & Safety -----------------------------------------------------

interface CertificationOut {
  id: string; name: string; certificate_number: string | null; issuing_organization: string | null;
  issue_date: string | null; expiry_date: string | null; scope: string | null; document_url: string | null;
}

export function QualityAndSafety() {
  const { data, isLoading } = useQuery({
    queryKey: ["certifications-public"],
    queryFn: () => api.get<CertificationOut[]>("/certifications/public"),
  });

  return (
    <div className="container page-section">
      <Hero title="Quality & Safety" subtitle="Information about Rockstar Organics quality, safety and compliance practices." />
      <OverviewPanel section="quality_safety" fallback="Quality information pending verification." />

      <div className="panel" style={{ marginTop: 24 }}>
        <h2>Certifications</h2>
        {isLoading && <div className="loading-state">Loading...</div>}
        {data && data.length === 0 && <p className="small muted">No verified certifications are currently available.</p>}
        {data && data.length > 0 && (
          <div className="grid cols-2">
            {data.map((c) => (
              <div className="panel" key={c.id}>
                <h3>{c.name}</h3>
                {c.issuing_organization && <p className="small muted">Issued by {c.issuing_organization}</p>}
                {c.certificate_number && <p className="small muted">Certificate no. {c.certificate_number}</p>}
                <p className="small muted">{c.scope || PENDING}</p>
                {c.document_url && <p className="small"><a href={mediaUrl(c.document_url)} target="_blank" rel="noreferrer">View certificate</a></p>}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="panel" style={{ marginTop: 24 }}>
        <div className="section-heading">
          <h2>Official certificates &amp; documents</h2>
          <a href="/certificates">View all</a>
        </div>
        <p className="small muted">
          Verified quality/safety documents are published on the <a href="/certificates">certificates &amp; documents</a> page
          once reviewed and approved by staff.
        </p>
      </div>
    </div>
  );
}

// --- Sustainability ---------------------------------------------------

interface SustainabilityInitiativeOut {
  id: string; title: string; description: string | null; category: string | null; measurable_results: string | null; photo_url: string | null;
}

export function Sustainability() {
  const { data, isLoading } = useQuery({
    queryKey: ["sustainability-initiatives-public"],
    queryFn: () => api.get<SustainabilityInitiativeOut[]>("/sustainability/initiatives/public"),
  });

  return (
    <div className="container page-section">
      <Hero title="Sustainability" subtitle="Information about Rockstar Organics sustainability initiatives and environmental practices." />
      <OverviewPanel section="sustainability" fallback="Sustainability information pending verification." />
      <div style={{ marginTop: 24 }}>
        <h2>Initiatives</h2>
        {isLoading && <div className="loading-state">Loading...</div>}
        {data && data.length === 0 && <p className="small muted">Sustainability photographs pending verification.</p>}
        {data && data.length > 0 && (
          <div className="grid cols-2">
            {data.map((i) => (
              <div className="panel" key={i.id}>
                {i.photo_url && <img src={mediaUrl(i.photo_url)} alt="" style={{ width: "100%", aspectRatio: "16/9", objectFit: "cover", borderRadius: "var(--radius-md)", marginBottom: 8 }} />}
                <h3>{i.title}</h3>
                {i.category && <p className="small muted">{i.category}</p>}
                <p className="small muted">{i.description || PENDING}</p>
                {i.measurable_results && <p className="small">{i.measurable_results}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function FarmerStories() {
  return (
    <div className="container page-section">
      <h1>Farmer Stories</h1>
      <div className="panel">
        <p className="muted">
          Real farmer stories and testimonials will appear here once submitted and verified - Rockstar Organics
          never publishes a testimonial that has not been confirmed with the farmer named in it.
        </p>
        <p className="small muted">No verified farmer stories are available yet.</p>
      </div>
    </div>
  );
}

export function Careers() {
  return (
    <div className="container page-section">
      <h1>Careers</h1>
      <div className="panel">
        <p className="muted">Current openings at Rockstar Organics are listed here once published by staff.</p>
        <p className="small muted">No open positions are currently listed.</p>
        <p className="small muted">
          For a general enquiry about opportunities at Rockstar Organics, use the <a href="/contact">contact form</a>.
        </p>
      </div>
    </div>
  );
}
