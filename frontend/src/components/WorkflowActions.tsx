import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { StatusBadge } from "./StatusBadge";

const SETTINGS_MANAGER_ROLES = ["super_admin", "admin"];

interface WorkflowActionsProps {
  basePath: string;
  itemId: string;
  status: string;
  userRole: string;
  queryKey: unknown[];
  onError: (message: string) => void;
}

/** Renders the valid next actions for a corporate-content record's current
 * status, calling the shared workflow endpoints every domain router
 * registers via app.core.verifiable_workflow. Approve/publish/archive are
 * hidden for anyone who isn't an owner/admin - the backend enforces this
 * regardless, this just avoids offering a button that will 403. */
export function WorkflowActions({ basePath, itemId, status, userRole, queryKey, onError }: WorkflowActionsProps) {
  const qc = useQueryClient();
  const canApprove = SETTINGS_MANAGER_ROLES.includes(userRole);

  const action = useMutation({
    mutationFn: (step: string) => api.post(`${basePath}/${itemId}/${step}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey }),
    onError: (e: unknown) => onError(e instanceof ApiError ? e.message : "Action failed."),
  });

  const actionWithNote = useMutation({
    mutationFn: ({ step, note }: { step: string; note: string }) => api.post(`${basePath}/${itemId}/${step}`, { note }),
    onSuccess: () => qc.invalidateQueries({ queryKey }),
    onError: (e: unknown) => onError(e instanceof ApiError ? e.message : "Action failed."),
  });

  const handleNoteAction = (step: "reject" | "request-revision") => {
    const note = window.prompt(step === "reject" ? "Reason for rejection (optional):" : "Revision notes (optional):") || "";
    actionWithNote.mutate({ step, note });
  };

  return (
    <div className="inline" style={{ flexWrap: "wrap" }}>
      <StatusBadge status={status} />
      {status === "draft" && <button className="btn btn-ghost btn-sm" onClick={() => action.mutate("submit")}>Submit for review</button>}
      {status === "rejected" && <button className="btn btn-ghost btn-sm" onClick={() => action.mutate("submit")}>Resubmit</button>}
      {status === "submitted" && <button className="btn btn-ghost btn-sm" onClick={() => action.mutate("review")}>Start review</button>}
      {(status === "submitted" || status === "under_review") && (
        <button className="btn btn-ghost btn-sm" onClick={() => action.mutate("verify")}>Verify</button>
      )}
      {(status === "under_review" || status === "verified") && (
        <button className="btn btn-ghost btn-sm" onClick={() => handleNoteAction("reject")}>Reject</button>
      )}
      {status !== "published" && status !== "archived" && (
        <button className="btn btn-ghost btn-sm" onClick={() => handleNoteAction("request-revision")}>Request revision</button>
      )}
      {canApprove && status === "verified" && <button className="btn btn-ghost btn-sm" onClick={() => action.mutate("approve")}>Approve</button>}
      {canApprove && status === "approved" && <button className="btn btn-primary btn-sm" onClick={() => action.mutate("publish")}>Publish</button>}
      {canApprove && status === "published" && <button className="btn btn-ghost btn-sm" onClick={() => action.mutate("unpublish")}>Unpublish</button>}
      {canApprove && status !== "archived" && <button className="btn btn-danger btn-sm" onClick={() => action.mutate("archive")}>Archive</button>}
      {canApprove && status === "archived" && <button className="btn btn-ghost btn-sm" onClick={() => action.mutate("restore")}>Restore</button>}
    </div>
  );
}
