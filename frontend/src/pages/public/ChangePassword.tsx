import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { PasswordInput } from "../../components/PasswordInput";

const STAFF_ROLES = ["super_admin", "admin", "content_manager", "sales_manager", "field_officer"];

export function ChangePassword() {
  const { user, loading, refresh } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (!loading && !user) return <Navigate to="/login" replace />;

  const dashboardPath = user
    ? user.role === "farmer" ? "/farmer" : user.role === "dealer" ? "/dealer" : STAFF_ROLES.includes(user.role) ? "/staff" : "/"
    : "/";

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Change your password</h1>
      {user?.must_change_password && (
        <div className="alert alert-info">
          Your account was created with a temporary password. Set a new password to continue.
        </div>
      )}
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setPending(true);
            setError(null);
            try {
              await api.post("/auth/change-password", { current_password: currentPassword, new_password: newPassword });
              await refresh();
              navigate(dashboardPath);
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Unable to change password.");
            } finally {
              setPending(false);
            }
          }}
        >
          <div className="field"><label htmlFor="current_password">Current password</label>
            <PasswordInput id="current_password" required autoComplete="current-password" value={currentPassword} onChange={setCurrentPassword} /></div>
          <div className="field"><label htmlFor="new_password">New password</label>
            <PasswordInput id="new_password" required autoComplete="new-password" value={newPassword} onChange={setNewPassword} />
            <p className="hint">At least 10 characters, with a letter and a digit.</p></div>
          <button className="btn btn-primary" type="submit" disabled={pending}>{pending ? "Updating..." : "Change password"}</button>
        </form>
      </div>
    </div>
  );
}
