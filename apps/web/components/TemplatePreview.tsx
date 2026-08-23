"use client";

import { useState } from "react";

export default function TemplatePreview({ templateId }: { templateId: string }) {
  const [open, setOpen] = useState(false);
  const [scale, setScale] = useState(1);
  const [error, setError] = useState("");

  const MIN = 0.5;
  const MAX = 3;

  function reset() {
    setScale(1);
    setError("");
  }

  function openPreview() {
    reset();
    setOpen(true);
  }

  return (
    <>
      <button
        type="button"
        className="secondary"
        title="Preview this template (zoomable)"
        disabled={!templateId}
        onClick={openPreview}
      >
        Preview
      </button>

      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div
            className="modal preview-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="row">
              <h3 style={{ margin: 0 }}>Template preview</h3>
              <span className="spacer" />
              <div className="row" style={{ gap: 6 }}>
                <button className="secondary" onClick={() => setScale((s) => Math.max(MIN, s - 0.25))} title="Zoom out">
                  −
                </button>
                <span className="muted" style={{ minWidth: 44, textAlign: "center" }}>
                  {Math.round(scale * 100)}%
                </span>
                <button className="secondary" onClick={() => setScale((s) => Math.min(MAX, s + 0.25))} title="Zoom in">
                  +
                </button>
                <button className="secondary" onClick={reset} title="Reset zoom">
                  Reset
                </button>
                <button className="secondary" onClick={() => setOpen(false)}>
                  Close
                </button>
              </div>
            </div>

            <div className="preview-viewport">
              {error ? (
                <p className="error">{error}</p>
              ) : (
                <img
                  src={`/api/templates/${templateId}/preview`}
                  alt="Template preview"
                  style={{ transform: `scale(${scale})` }}
                  onError={() => setError("Preview is not available yet.")}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}