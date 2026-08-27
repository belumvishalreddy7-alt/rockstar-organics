import { useQuery } from "@tanstack/react-query";
import { api, mediaUrl } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";

interface CompanyDocument {
  id: string; title: string; document_type: string; reference_number: string | null;
  issuing_authority: string | null; issue_date: string | null; expiry_date: string | null;
  verification_status: string; download_url: string;
}

const TYPE_LABELS: Record<string, string> = {
  company_certificate: "Company certificate", registration_document: "Registration document",
  manufacturing_certificate: "Manufacturing certificate", quality_certificate: "Quality certificate",
  compliance_document: "Compliance document", licence: "Licence", product_certificate: "Product certificate",
  other: "Other document",
};

export function Certificates() {
  const { data, isLoading } = useQuery({ queryKey: ["public-company-documents"], queryFn: () => api.get<CompanyDocument[]>("/company/documents") });

  return (
    <div className="container page-section">
      <h1>Certificates &amp; official documents</h1>
      <p className="muted">
        A document appears here only after it has been reviewed and verified by Rockstar Organics staff. Uploading
        a document does not make it verified or public by itself.
      </p>
      {isLoading && <div className="loading-state">Loading documents...</div>}
      {data && data.length === 0 && (
        <EmptyState title="No verified documents are published yet.">
          <p className="small">Information pending verification.</p>
        </EmptyState>
      )}
      <div className="grid cols-2">
        {data?.map((d) => (
          <div className="panel" key={d.id}>
            <h3>{d.title}</h3>
            <p className="small muted">{TYPE_LABELS[d.document_type] || d.document_type}</p>
            {d.reference_number && <p className="small muted">Reference: {d.reference_number}</p>}
            <p className="small muted">Issuing authority: {d.issuing_authority || "Information pending verification."}</p>
            <p className="small muted">
              Issued: {d.issue_date ? new Date(d.issue_date).toLocaleDateString() : "Information pending verification."}
              {d.expiry_date ? ` · Expires: ${new Date(d.expiry_date).toLocaleDateString()}` : ""}
            </p>
            <a className="btn btn-secondary btn-sm" href={mediaUrl(d.download_url)} target="_blank" rel="noreferrer">
              View document
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
