import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import { PhoneContact } from "../../components/PhoneContact";

interface EnquiryRow { id: string; reference_number: string; enquiry_type: string; name: string; phone: string | null; status: string; created_at: string; }

const STATUSES = ["new", "assigned", "in_progress", "waiting_for_customer", "resolved", "closed", "spam", "cancelled"];

export function EnquiryQueue() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["enquiries"], queryFn: () => api.get<EnquiryRow[]>("/enquiries") });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/enquiries/${id}/status/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enquiries"] }),
  });

  if (isLoading) return <div className="loading-state">Loading enquiries...</div>;
  if (!data || data.length === 0) return <EmptyState title="No enquiries yet." />;

  return (
    <div>
      <h2>Enquiries</h2>
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Reference</th><th>Type</th><th>Name</th><th>Phone</th><th>Status</th><th>Update status</th></tr></thead>
          <tbody>
            {data.map((e) => (
              <tr key={e.id}>
                <td>{e.reference_number}</td><td>{e.enquiry_type.replace("_", " ")}</td><td>{e.name}</td>
                <td><PhoneContact phone={e.phone} /></td>
                <td><StatusBadge status={e.status} /></td>
                <td>
                  <select value={e.status} onChange={(ev) => changeStatus.mutate({ id: e.id, status: ev.target.value })}>
                    {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
