export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="empty-state" role="status">
      <p style={{ fontWeight: 600, marginBottom: children ? 6 : 0 }}>{title}</p>
      {children}
    </div>
  );
}
