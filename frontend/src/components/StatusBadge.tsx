const TONE_MAP: Record<string, string> = {
  draft: "neutral", in_review: "warning", approved: "accent", published: "success", unpublished: "neutral",
  archived: "neutral", rejected: "danger", new: "accent", under_review: "warning", approved_status: "success",
  pending: "warning", spam: "danger", resolved: "success", closed: "neutral", cancelled: "neutral",
  active: "success", suspended: "danger", disabled: "neutral", withdrawn: "neutral", contacted: "accent",
  on_hold: "warning", information_required: "warning",
};

export function StatusBadge({ status }: { status: string }) {
  const tone = TONE_MAP[status] || "neutral";
  const label = status.replace(/_/g, " ");
  return <span className={`badge badge-${tone}`}>{label}</span>;
}
