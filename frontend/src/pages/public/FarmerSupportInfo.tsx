import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export function FarmerSupportInfo() {
  const { user } = useAuth();
  return (
    <div className="container page-section">
      <h1>Farmer support</h1>
      <div className="panel">
        <h2>How it works</h2>
        <p>
          Submit a support request describing your crop, location, and the issue you are seeing. Include your
          district and mandal so it can be reviewed by staff and, where appropriate, shared with a dealer who
          services your area.
        </p>
        <p>
          Requests are reviewed by people, not automatically. Rockstar Organics does not automatically diagnose
          your crop or prescribe a product from your description; a staff member, and where relevant a field
          officer visit, is part of the process.
        </p>
        <h3>Useful information to include</h3>
        <p>Crop, crop stage, when the issue started, what part of the plant is affected, recent treatments applied, and photos if you have them.</p>
        <h3>What happens to your data</h3>
        <p>Your case details are shared only with the staff member or dealer assigned to your case. Private notes made by staff are never shown to you.</p>
        <h3>Status flow</h3>
        <p>New → Triage → Assigned → In Progress → (Visit Requested/Scheduled if needed) → Resolved → Closed.</p>
      </div>
      {user?.role === "farmer" ? (
        <Link className="btn btn-primary" to="/farmer/cases/new">Submit a support request</Link>
      ) : (
        <Link className="btn btn-primary" to="/register">Create a farmer account to submit a request</Link>
      )}
    </div>
  );
}
