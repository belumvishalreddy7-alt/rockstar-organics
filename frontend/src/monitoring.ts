/**
 * Frontend error tracking (Sentry), initialized only when a DSN is provided
 * via VITE_SENTRY_DSN at build time. With no DSN configured, `initMonitoring`
 * is a no-op - same "explicit opt-in, no silent fake state" rule used for
 * the backend's SENTRY_DSN / EMAIL_PROVIDER_ENABLED settings.
 */
import * as Sentry from "@sentry/react";

export function initMonitoring() {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.1,
    // No session replay / PII capture by default - keep this to error +
    // basic performance signal unless a team deliberately opts into more.
  });
}

export { Sentry };
