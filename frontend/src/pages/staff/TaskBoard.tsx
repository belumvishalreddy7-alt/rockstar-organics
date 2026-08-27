import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";

interface TaskRow { id: string; title: string; description: string | null; priority: string; status: string; due_date: string | null; overdue: boolean; }

export function TaskBoard() {
  const qc = useQueryClient();
  const [mineOnly, setMineOnly] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["tasks", mineOnly], queryFn: () => api.get<TaskRow[]>(`/tasks${mineOnly ? "?mine_only=true" : ""}`) });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.post(`/tasks/${id}/status/${status}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  return (
    <div>
      <div className="section-heading">
        <h2>Follow-up tasks</h2>
        <label className="small"><input type="checkbox" checked={mineOnly} onChange={(e) => setMineOnly(e.target.checked)} /> Show only my tasks</label>
      </div>
      {isLoading && <div className="loading-state">Loading tasks...</div>}
      {data && data.length === 0 && <EmptyState title="No follow-up tasks." />}
      <div className="stack">
        {data?.map((t) => (
          <div className="panel" key={t.id}>
            <div className="inline">
              <strong>{t.title}</strong>
              <StatusBadge status={t.status} />
              {t.overdue && <span className="badge badge-danger">Overdue</span>}
              <span className="small muted">Priority: {t.priority}</span>
            </div>
            {t.description && <p className="small">{t.description}</p>}
            {t.due_date && <p className="small muted">Due: {new Date(t.due_date).toLocaleDateString()}</p>}
            {t.status !== "completed" && t.status !== "cancelled" && (
              <div className="inline">
                {t.status !== "in_progress" && <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: t.id, status: "in_progress" })}>Mark in progress</button>}
                <button className="btn btn-primary btn-sm" onClick={() => changeStatus.mutate({ id: t.id, status: "completed" })}>Mark completed</button>
                <button className="btn btn-ghost btn-sm" onClick={() => changeStatus.mutate({ id: t.id, status: "cancelled" })}>Cancel</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
