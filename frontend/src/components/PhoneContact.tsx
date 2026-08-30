/** Renders a phone number as a click-to-call link plus a WhatsApp
 * "chat" link (wa.me - no API/integration needed, just opens WhatsApp
 * with the number pre-filled). Indian mobile numbers are stored as plain
 * 10 digits with no country code, so a bare 10-digit value is prefixed
 * with 91 for the wa.me link; anything else is passed through as-is. */
export function PhoneContact({ phone }: { phone: string | null | undefined }) {
  if (!phone) return <span className="muted">Not provided</span>;

  const digits = phone.replace(/\D/g, "");
  const whatsappNumber = digits.length === 10 ? `91${digits}` : digits;

  return (
    <span className="inline" style={{ gap: 6 }}>
      <a href={`tel:${digits}`}>{phone}</a>
      <a href={`https://wa.me/${whatsappNumber}`} target="_blank" rel="noreferrer" title="Chat on WhatsApp" aria-label="Chat on WhatsApp">
        WhatsApp
      </a>
    </span>
  );
}
