import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const STAFF_ROLES = ["super_admin", "admin", "content_manager", "sales_manager", "field_officer"];

export function SiteHeader() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const dashboardPath = user
    ? user.role === "farmer"
      ? "/farmer"
      : user.role === "dealer"
      ? "/dealer"
      : user.role === "distributor"
      ? "/distributor"
      : STAFF_ROLES.includes(user.role)
      ? "/staff"
      : "/"
    : "/";

  return (
    <header className="site-header">
      <div className="container">
        <a className="brand" href="/">
          <span className="brand-mark">Rockstar Organics</span>
          <span className="brand-tag">Hyderabad &amp; Ranga Reddy region</span>
        </a>
        <button className="nav-toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="main-nav">
          Menu
        </button>
        <nav id="main-nav" className={`main-nav ${open ? "open" : ""}`} aria-label="Main navigation">
          <NavLink to="/" end onClick={() => setOpen(false)}>Home</NavLink>
          <NavLink to="/about" onClick={() => setOpen(false)}>About Rockstar Organics</NavLink>
          <NavLink to="/products" onClick={() => setOpen(false)}>Products</NavLink>
          <NavLink to="/dealers" onClick={() => setOpen(false)}>Dealers</NavLink>
          <NavLink to="/distributors" onClick={() => setOpen(false)}>Distributors</NavLink>
          <NavLink to="/contact" onClick={() => setOpen(false)}>Contact</NavLink>
          {user ? (
            <>
              <NavLink to={dashboardPath} onClick={() => setOpen(false)}>My account</NavLink>
              <NavLink to="/change-password" onClick={() => setOpen(false)}>Change password</NavLink>
              <button
                className="nav-link"
                onClick={async () => {
                  await logout();
                  setOpen(false);
                  navigate("/");
                }}
              >
                Sign out
              </button>
            </>
          ) : (
            <NavLink to="/login" onClick={() => setOpen(false)}>Login</NavLink>
          )}
        </nav>
      </div>
    </header>
  );
}
