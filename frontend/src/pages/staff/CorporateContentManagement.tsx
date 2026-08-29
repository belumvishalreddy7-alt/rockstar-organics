import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { CorporateEntityManager, type FieldConfig } from "../../components/CorporateEntityManager";
import { PageContentEditor } from "../../components/PageContentEditor";

const CONTENT_MANAGER_ROLES = ["super_admin", "admin", "content_manager"];

const LEADERSHIP_FIELDS: FieldConfig[] = [
  { key: "full_name", label: "Full name", type: "text" },
  { key: "position", label: "Position / designation", type: "text" },
  { key: "biography", label: "Biography", type: "textarea" },
  { key: "responsibilities", label: "Areas of responsibility", type: "textarea" },
  { key: "experience", label: "Professional experience", type: "textarea" },
  { key: "education", label: "Education", type: "textarea" },
  { key: "profile_url", label: "Official profile URL (LinkedIn, etc.)", type: "url" },
  { key: "joining_date", label: "Joining date", type: "date" },
  { key: "sort_order", label: "Display order", type: "number" },
];

const FACILITY_FIELDS: FieldConfig[] = [
  { key: "name", label: "Facility name", type: "text" },
  { key: "facility_type", label: "Facility type", type: "text" },
  { key: "address", label: "Address", type: "textarea" },
  { key: "latitude", label: "Latitude", type: "number" },
  { key: "longitude", label: "Longitude", type: "number" },
  { key: "description", label: "Description", type: "textarea" },
  { key: "capabilities", label: "Capabilities", type: "textarea" },
  { key: "certifications_text", label: "Certifications", type: "textarea" },
  { key: "capacity", label: "Capacity", type: "text" },
  { key: "established_date", label: "Established date", type: "date" },
  { key: "contact_info", label: "Contact information", type: "text" },
];

const RESEARCH_FACILITY_FIELDS: FieldConfig[] = [
  { key: "name", label: "Facility name", type: "text" },
  { key: "facility_type", label: "Facility type", type: "text" },
  { key: "location", label: "Location", type: "text" },
  { key: "description", label: "Description", type: "textarea" },
  { key: "capabilities", label: "Research capabilities", type: "textarea" },
  { key: "equipment_info", label: "Equipment information", type: "textarea" },
];

const RESEARCH_AREA_FIELDS: FieldConfig[] = [
  { key: "title", label: "Title", type: "text" },
  { key: "description", label: "Description", type: "textarea" },
  { key: "sort_order", label: "Display order", type: "number" },
];

const CERTIFICATION_FIELDS: FieldConfig[] = [
  { key: "name", label: "Certification name", type: "text" },
  { key: "certificate_number", label: "Certificate number", type: "text" },
  { key: "issuing_organization", label: "Issuing organization", type: "text" },
  { key: "issue_date", label: "Issue date", type: "date" },
  { key: "expiry_date", label: "Expiry date", type: "date" },
  { key: "scope", label: "Scope", type: "textarea" },
];

const SUSTAINABILITY_FIELDS: FieldConfig[] = [
  { key: "title", label: "Title", type: "text" },
  { key: "description", label: "Description", type: "textarea" },
  { key: "category", label: "Category", type: "text" },
  { key: "start_date", label: "Start date", type: "date" },
  { key: "measurable_results", label: "Measurable results (only if verified)", type: "textarea" },
];

const SECTIONS = [
  { id: "leadership", label: "Leadership" },
  { id: "manufacturing", label: "Manufacturing" },
  { id: "research_development", label: "Research & Development" },
  { id: "quality_safety", label: "Quality & Safety" },
  { id: "sustainability", label: "Sustainability" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

export function CorporateContentManagement() {
  const { user } = useAuth();
  const [section, setSection] = useState<SectionId>("leadership");

  if (!user || !CONTENT_MANAGER_ROLES.includes(user.role)) {
    return (
      <div>
        <h2>Corporate content</h2>
        <p className="muted">Only the owner or a manager can manage corporate content.</p>
      </div>
    );
  }

  return (
    <div>
      <h2>Corporate content</h2>
      <p className="small muted">
        Manage the Leadership, Manufacturing, Research &amp; Development, Quality &amp; Safety and Sustainability pages.
        Nothing reaches the public site until it is verified, approved and published.
      </p>
      <div className="inline" style={{ marginBottom: 16 }}>
        {SECTIONS.map((s) => (
          <button key={s.id} className={`btn btn-sm ${section === s.id ? "btn-primary" : "btn-ghost"}`} onClick={() => setSection(s.id)}>
            {s.label}
          </button>
        ))}
      </div>

      {section === "leadership" && (
        <CorporateEntityManager title="Leadership profiles" basePath="/leadership" labelField="full_name" subLabelField="position"
          fields={LEADERSHIP_FIELDS} userRole={user.role} />
      )}

      {section === "manufacturing" && (
        <>
          <PageContentEditor
            section="manufacturing" userRole={user.role}
            fieldKeys={[
              { key: "overview", label: "Overview" }, { key: "capabilities", label: "Manufacturing capabilities" },
              { key: "processes", label: "Processes" }, { key: "infrastructure", label: "Infrastructure" },
              { key: "quality_systems", label: "Quality systems" }, { key: "capacity_information", label: "Capacity information" },
              { key: "technology_information", label: "Technology information" }, { key: "safety_practices", label: "Safety practices" },
              { key: "environmental_practices", label: "Environmental practices" },
            ]}
          />
          <CorporateEntityManager title="Manufacturing facilities" basePath="/manufacturing/facilities" labelField="name" subLabelField="facility_type"
            fields={FACILITY_FIELDS} userRole={user.role} />
        </>
      )}

      {section === "research_development" && (
        <>
          <PageContentEditor
            section="research_development" userRole={user.role}
            fieldKeys={[
              { key: "overview", label: "R&D overview" }, { key: "research_focus", label: "Research focus" },
              { key: "development_activities", label: "Development activities" }, { key: "innovation_approach", label: "Innovation approach" },
              { key: "testing_activities", label: "Testing activities" }, { key: "product_development_process", label: "Product development process" },
              { key: "verified_collaborations", label: "Verified collaborations" }, { key: "publications", label: "Publications" },
            ]}
          />
          <CorporateEntityManager title="Research areas" basePath="/research/areas" labelField="title"
            fields={RESEARCH_AREA_FIELDS} userRole={user.role} />
          <CorporateEntityManager title="Research facilities" basePath="/research/facilities" labelField="name" subLabelField="facility_type"
            fields={RESEARCH_FACILITY_FIELDS} userRole={user.role} />
        </>
      )}

      {section === "quality_safety" && (
        <>
          <PageContentEditor
            section="quality_safety" userRole={user.role}
            fieldKeys={[
              { key: "quality_philosophy", label: "Quality philosophy" }, { key: "quality_control_processes", label: "Quality-control processes" },
              { key: "testing_information", label: "Testing information" }, { key: "quality_assurance", label: "Quality assurance" },
              { key: "traceability", label: "Traceability" }, { key: "compliance_information", label: "Compliance information" },
              { key: "product_safety", label: "Product safety information" }, { key: "workplace_safety", label: "Workplace safety" },
              { key: "manufacturing_safety", label: "Manufacturing safety" }, { key: "handling_information", label: "Handling information" },
              { key: "storage_information", label: "Storage information" }, { key: "regulatory_information", label: "Regulatory information" },
            ]}
          />
          <CorporateEntityManager title="Certifications" basePath="/certifications" labelField="name" subLabelField="issuing_organization"
            fields={CERTIFICATION_FIELDS} userRole={user.role} />
        </>
      )}

      {section === "sustainability" && (
        <>
          <PageContentEditor
            section="sustainability" userRole={user.role}
            fieldKeys={[
              { key: "approach", label: "Sustainability approach" }, { key: "environmental_initiatives", label: "Environmental initiatives" },
              { key: "resource_management", label: "Resource management" }, { key: "waste_management", label: "Waste management" },
              { key: "energy_management", label: "Energy management" }, { key: "water_management", label: "Water management" },
              { key: "responsible_operations", label: "Responsible operations" }, { key: "community_initiatives", label: "Community initiatives" },
              { key: "sustainability_goals", label: "Sustainability goals" },
            ]}
          />
          <CorporateEntityManager title="Sustainability initiatives" basePath="/sustainability/initiatives" labelField="title" subLabelField="category"
            fields={SUSTAINABILITY_FIELDS} userRole={user.role} />
        </>
      )}
    </div>
  );
}
