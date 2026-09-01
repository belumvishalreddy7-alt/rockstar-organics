import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  must_change_password: boolean;
}

export interface OtpRequired {
  otp_required: true;
  email: string;
  message: string;
  email_sent: boolean;
  dev_otp_code?: string;
}

export type LoginResult = CurrentUser | OtpRequired;

function isOtpRequired(result: LoginResult): result is OtpRequired {
  return "otp_required" in result;
}

interface AuthContextValue {
  user: CurrentUser | null;
  loading: boolean;
  sessionExpired: boolean;
  clearSessionExpired: () => void;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<LoginResult>;
  verifyLoginOtp: (email: string, code: string) => Promise<CurrentUser>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  const refresh = async () => {
    try {
      const me = await api.get<CurrentUser | null>("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    // Dispatched by api/client.ts whenever a request comes back 401 while
    // this tab still thinks it has a valid session (expired, or invalidated
    // by signing in elsewhere - only one session per account stays active).
    // Clearing `user` here is what actually fixes the "button does nothing"
    // symptom: ProtectedRoute already redirects to /login the instant `user`
    // is null, it just never found out the old session had died.
    const onExpired = () => {
      setUser((current) => (current ? null : current));
      setSessionExpired(true);
    };
    window.addEventListener("rso:session-expired", onExpired);
    return () => window.removeEventListener("rso:session-expired", onExpired);
  }, []);

  const login = async (email: string, password: string) => {
    const result = await api.post<LoginResult>("/auth/login", { email, password });
    // Staff, dealer, and distributor accounts stop here with an emailed
    // code to confirm (see OTP_LOGIN_ROLES in the backend) - no session is
    // issued, and therefore no user state to set, until verifyLoginOtp
    // completes. Farmers skip this and get a session immediately.
    if (!isOtpRequired(result)) setUser(result);
    setSessionExpired(false);
    return result;
  };

  const verifyLoginOtp = async (email: string, code: string) => {
    const u = await api.post<CurrentUser>("/auth/login/verify-otp", { email, code });
    setUser(u);
    setSessionExpired(false);
    return u;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      // Clear client-side state even if the request failed (network blip,
      // already-expired session) - staying "logged in" in the UI after the
      // user explicitly asked to sign out would be a silent-failure bug,
      // and the httponly session cookie expires on its own regardless.
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, sessionExpired, clearSessionExpired: () => setSessionExpired(false), refresh, login, verifyLoginOtp, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
