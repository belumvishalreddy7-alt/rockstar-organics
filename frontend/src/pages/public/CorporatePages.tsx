/**
 * Dedicated corporate pages (Leadership, Manufacturing, R&D, Quality &
 * Safety, Sustainability, Farmer Stories, Careers) split out from the
 * subsections previously embedded inline in About.tsx, so each has its
 * own route/URL for navigation and SEO purposes (page titles for these
 * routes are set centrally in hooks/useRouteTitle.ts).
 *
 * None of these invent company information: every one of them states
 * "Information pending verification" for content not yet supplied by
 * Rockstar Organics, exactly like the existing About/Contact pages do.
 * When real content exists, replace the placeholder paragraph in the
 * relevant component below - the page structure itself does not change.
 */
const PENDING = "Information pending verification.";

function CorporatePage({ title, intro }: { title: string; intro: string }) {
  return (
    <div className="container page-section">
      <h1>{title}</h1>
      <div className="panel">
        <p className="muted">{intro}</p>
        <p className="small muted">{PENDING}</p>
      </div>
    </div>
  );
}

export function Leadership() {
  return (
    <CorporatePage
      title="Leadership"
      intro="Rockstar Organics' leadership team information is published here only after verification by the company."
    />
  );
}

export function Manufacturing() {
  return (
    <CorporatePage
      title="Manufacturing"
      intro="Details of Rockstar Organics' manufacturing facilities, capacity, and processes are published here only after verification."
    />
  );
}

export function ResearchAndDevelopment() {
  return (
    <CorporatePage
      title="Research & Development"
      intro="Rockstar Organics' R&D programs, facilities, and focus areas are published here only after verification."
    />
  );
}

export function QualityAndSafety() {
  return (
    <div className="container page-section">
      <h1>Quality &amp; Safety</h1>
      <div className="panel">
        <p className="muted">
          Rockstar Organics' quality control processes, safety standards, and testing procedures are published
          here only after verification.
        </p>
        <p className="small muted">{PENDING}</p>
      </div>
      <div className="panel" style={{ marginTop: 24 }}>
        <div className="section-heading">
          <h2>Official certificates &amp; documents</h2>
          <a href="/certificates">View all</a>
        </div>
        <p className="small muted">
          Verified quality/safety certificates are published on the <a href="/certificates">certificates &amp; documents</a> page
          once reviewed and approved by staff.
        </p>
      </div>
    </div>
  );
}

export function Sustainability() {
  return (
    <CorporatePage
      title="Sustainability"
      intro="Rockstar Organics' sustainability practices and initiatives are published here only after verification."
    />
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
