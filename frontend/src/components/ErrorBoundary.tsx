import { Component, type ErrorInfo, type ReactNode } from "react";
import { Sentry } from "../monitoring";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Top-level error boundary so a render-time exception in any page shows a
 * recoverable "something went wrong" screen instead of a blank white page,
 * and is reported to Sentry when monitoring is configured (see
 * src/monitoring.ts). This does not replace per-request error handling in
 * the API client - it's the last line of defense for render-time bugs.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    Sentry.captureException(error, { extra: { componentStack: info.componentStack } });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container page-section">
          <h1>Something went wrong</h1>
          <p className="muted">
            An unexpected error occurred while rendering this page. Reloading usually fixes it; if it
            keeps happening, please contact support.
          </p>
          <button className="btn btn-secondary" onClick={() => window.location.assign("/")}>
            Return home
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
