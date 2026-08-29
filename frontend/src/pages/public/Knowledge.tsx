import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";

interface ArticleSummary { id: string; title: string; slug: string; summary: string | null; topic: string | null; }
interface ArticleDetail extends ArticleSummary { body: string; crops: string | null; region: string | null; disclaimer: string; published_date: string | null; }

export function Knowledge() {
  const { data, isLoading } = useQuery({ queryKey: ["knowledge-public"], queryFn: () => api.get<ArticleSummary[]>("/knowledge/public") });
  return (
    <div className="container page-section">
      <h1>Crop knowledge centre</h1>
      {isLoading && <div className="loading-state">Loading articles...</div>}
      {data && data.length === 0 && (
        <EmptyState title="No published knowledge articles yet.">
          <p className="small">Articles appear here once written by content staff and reviewed for accuracy.</p>
        </EmptyState>
      )}
      <div className="grid cols-2">
        {data?.map((a) => (
          <div className="panel" key={a.id}>
            <h3><Link to={`/knowledge/${a.slug}`}>{a.title}</Link></h3>
            {a.topic && <p className="small muted">Topic: {a.topic}</p>}
            <p className="small">{a.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function KnowledgeDetail() {
  const { slug } = useParams();
  const { data, isLoading, isError } = useQuery({ queryKey: ["knowledge-detail", slug], queryFn: () => api.get<ArticleDetail>(`/knowledge/public/${slug}`) });
  useDocumentTitle(data ? `${data.title} | Rockstar Organics` : "Knowledge Article | Rockstar Organics");
  if (isLoading) return <div className="container page-section loading-state">Loading article...</div>;
  if (isError || !data) return <div className="container page-section"><div className="alert alert-error">Article not found.</div></div>;
  return (
    <div className="container page-section">
      <h1>{data.title}</h1>
      {data.topic && <p className="muted">Topic: {data.topic}{data.crops ? ` · Crops: ${data.crops}` : ""}{data.region ? ` · Region: ${data.region}` : ""}</p>}
      <div className="panel">
        <p>{data.body}</p>
        <div className="alert alert-info">{data.disclaimer}</div>
      </div>
    </div>
  );
}
