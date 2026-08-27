import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { api, ApiError } from "../../api/client";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Sign in</h1>
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setPending(true);
            setError(null);
            try {
              const user = await login(email, password);
              if (user.role === "farmer") navigate("/farmer");
              else if (user.role === "dealer") navigate("/dealer");
              else if (user.role === "distributor") navigate("/distributor");
              else navigate("/staff");
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Unable to sign in.");
            } finally {
              setPending(false);
            }
          }}
        >
          <div className="field"><label htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <div className="field"><label htmlFor="password">Password</label>
            <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
          <button className="btn btn-primary" type="submit" disabled={pending}>{pending ? "Signing in..." : "Sign in"}</button>
        </form>
        <p className="small" style={{ marginTop: 12 }}>
          <Link to="/forgot-password">Forgot your password?</Link> · <Link to="/signup">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

export function Register() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Create a farmer account</h1>
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setPending(true);
            setError(null);
            try {
              await api.post("/auth/register", form);
              await refresh();
              navigate("/farmer");
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Unable to register.");
            } finally {
              setPending(false);
            }
          }}
        >
          <div className="field"><label htmlFor="full_name">Full name</label>
            <input type="text" id="full_name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
          <div className="field"><label htmlFor="email">Email</label>
            <input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          <div className="field"><label htmlFor="phone">Phone (10-digit mobile)</label>
            <input type="text" id="phone" required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
          <div className="field"><label htmlFor="password">Password</label>
            <input id="password" type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <p className="hint">At least 10 characters, with uppercase, lowercase, and a digit.</p></div>
          <button className="btn btn-primary" type="submit" disabled={pending}>{pending ? "Creating account..." : "Create account"}</button>
        </form>
      </div>
    </div>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [devToken, setDevToken] = useState<string | null>(null);

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Reset your password</h1>
      <div className="panel">
        {message && <div className="alert alert-info">{message}</div>}
        {devToken && (
          <div className="alert alert-info">
            Development mode: <Link to={`/reset-password?token=${devToken}`}>use this reset link</Link> (would be emailed in production).
          </div>
        )}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const r = await api.post<{ ok: boolean; message: string; dev_reset_token?: string }>("/auth/forgot-password", { email });
            setMessage(r.message);
            setDevToken(r.dev_reset_token || null);
          }}
        >
          <div className="field"><label htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <button className="btn btn-primary" type="submit">Send reset link</button>
        </form>
      </div>
    </div>
  );
}

export function ResetPassword() {
  const params = new URLSearchParams(window.location.search);
  const [token, setToken] = useState(params.get("token") || "");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Set a new password</h1>
      <div className="panel">
        {done ? (
          <div className="alert alert-success">Password updated. <Link to="/login">Sign in</Link>.</div>
        ) : (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api.post("/auth/reset-password", { token, new_password: password });
                setDone(true);
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Unable to reset password.");
              }
            }}
          >
            {error && <div className="alert alert-error">{error}</div>}
            <div className="field"><label htmlFor="token">Reset token</label>
              <input type="text" id="token" required value={token} onChange={(e) => setToken(e.target.value)} /></div>
            <div className="field"><label htmlFor="new_password">New password</label>
              <input id="new_password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
            <button className="btn btn-primary" type="submit">Set new password</button>
          </form>
        )}
      </div>
    </div>
  );
}
