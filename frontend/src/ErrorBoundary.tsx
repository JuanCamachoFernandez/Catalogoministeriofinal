import { Component, type ErrorInfo, type ReactNode } from "react";

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error("Error no controlado en la interfaz", error, info); }
  render() {
    if (this.state.failed) return <main className="page-state min-h-screen"><h1>La página no pudo mostrarse</h1><p>Recargue la página para intentarlo nuevamente.</p><button className="btn" onClick={() => window.location.reload()}>Recargar</button></main>;
    return this.props.children;
  }
}
