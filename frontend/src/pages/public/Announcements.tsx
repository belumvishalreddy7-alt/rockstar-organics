import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";

interface AnnouncementSummary { id: string; title: string; slug: string; summary: string | null; publish_date: string | null; announcement_type: string; }
interface AnnouncementDetail extends AnnouncementSummary { body: string; }

export function Announcements() {
  const { data, isLoading } = useQuery({ queryKey: ["announcements-public"], queryFn: () => api.get<AnnouncementSummary[]>("/announcements/public") });
  return (
    <div className="container page-section">
      <h1>Announcements</h1>
      {isLoading && <div className="loading-state">Loading announcements...</div>}
      {data && data.length === 0 && <EmptyState title="No announcements published yet." />}
      <div className="stack">
        {data?.map((a) => (
          <div className="panel" key={a.id}>
            <h3><Link to={`/announcements/${a.slug}`}>{a.title}</Link></h3>
            <p className="small muted">{a.announcement_type} {a.publish_date ? `· ${new Date(a.publish_date).toLocaleDateString()}` : ""}</p>
            <p className="small">{a.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AnnouncementDetail() {
  const { slug } = useParams();
  const { data, isLoading, isError } = useQuery({ queryKey: ["announcement-detail", slug], queryFn: () => api.get<AnnouncementDetail>(`/announcements/public/${slug}`) });
  useDocumentTitle(data ? `${data.title} | Rockstar Organics` : "News | Rockstar Organics");
  if (isLoading) return <div className="container page-section loading-state">Loading...</div>;
  if (isError || !data) return <div className="container page-section"><div className="alert alert-error">Announcement not found.</div></div>;
  return (
    <div className="container page-section">
      <h1>{data.title}</h1>
      <p className="muted">{data.publish_date && new Date(data.publish_date).toLocaleDateString()}</p>
      <div className="panel"><p>{data.body}</p></div>
    </div>
  );
}
