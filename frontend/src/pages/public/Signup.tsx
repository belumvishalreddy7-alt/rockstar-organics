import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

interface DetailsForm {
  full_name: string; email: string; phone: string; password: string;
}

const initialDetails: DetailsForm = { full_name: "", email: "", phone: "", password: "" };

/**
 * Signup -> validation -> OTP verification -> account creation -> login,
 * per the real-world content spec. No account exists until the emailed
 * code is verified (see POST /api/auth/verify-otp) - this is deliberately
 * a separate flow from the older, direct /register page.
 */
export function Signup() {
  const [step, setStep] = useState<"details" | "otp">("details");
  const [details, setDetails] = useState<DetailsForm>(initialDetails);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState<boolean | null>(null);
  const navigate = useNavigate();
  const { refresh } = useAuth();

  const requestOtp = useMutation({
    mutationFn: () => api.post<{ ok: boolean; message: string; email_sent: boolean; dev_otp_code?: string }>("/auth/signup", details),
    onSuccess: (r) => {
      setError(null);
      setEmailSent(r.email_sent);
      setDevOtp(r.dev_otp_code || null);
      setStep("otp");
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  const verifyOtp = useMutation({
    mutationFn: () => api.post("/auth/verify-otp", { email: details.email, code }),
    onSuccess: async () => {
      setError(null);
      await refresh();
      navigate("/farmer");
    },
    onError: (e: unknown) => setError(e instanceof ApiError ? e.message : "Incorrect or expired verification code."),
  });

  return (
    <div className="container page-section" style={{ maxWidth: 420 }}>
      <h1>Create a farmer account</h1>
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}

        {step === "details" && (
          <form onSubmit={(e) => { e.preventDefault(); requestOtp.mutate(); }}>
            <div className="field"><label htmlFor="full_name">Full name</label>
              <input id="full_name" required value={details.full_name} onChange={(e) => setDetails({ ...details, full_name: e.target.value })} /></div>
            <div className="field"><label htmlFor="email">Email</label>
              <input id="email" type="email" required value={details.email} onChange={(e) => setDetails({ ...details, email: e.target.value })} /></div>
            <div className="field"><label htmlFor="phone">Phone (10-digit mobile)</label>
              <input id="phone" required value={details.phone} onChange={(e) => setDetails({ ...details, phone: e.target.value })} /></div>
            <div className="field"><label htmlFor="password">Password</label>
              <input id="password" type="password" required value={details.password} onChange={(e) => setDetails({ ...details, password: e.target.value })} />
              <p className="hint">At least 10 characters, with uppercase, lowercase, and a digit.</p></div>
            <button className="btn btn-primary" type="submit" disabled={requestOtp.isPending}>
              {requestOtp.isPending ? "Sending code..." : "Send verification code"}
            </button>
          </form>
        )}

        {step === "otp" && (
          <form onSubmit={(e) => { e.preventDefault(); verifyOtp.mutate(); }}>
            <p className="small muted">
              {emailSent
                ? <>We emailed a 6-digit verification code to <strong>{details.email}</strong>.</>
                : "Email delivery is not configured in this environment, so the code below is shown directly (this only happens in development)."}
            </p>
            {devOtp && (
              <div className="alert alert-info">Development mode: your code is <strong>{devOtp}</strong>.</div>
            )}
            <div className="field"><label htmlFor="code">Verification code</label>
              <input id="code" required inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} /></div>
            <button className="btn btn-primary" type="submit" disabled={verifyOtp.isPending}>
              {verifyOtp.isPending ? "Verifying..." : "Verify and create account"}
            </button>
            <button type="button" className="btn btn-ghost" style={{ marginLeft: 8 }} onClick={() => setStep("details")}>
              Back
            </button>
          </form>
        )}

        <p className="small" style={{ marginTop: 16 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
