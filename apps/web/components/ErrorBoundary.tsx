"use client";

import { Component, type ReactNode } from "react";

export default class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container" style={{ maxWidth: 480, marginTop: 80 }}>
          <div className="card">
            <h1>Something went wrong</h1>
            <p className="muted">
              An unexpected error occurred. Your work is safe — please try again.
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false });
              }}
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}