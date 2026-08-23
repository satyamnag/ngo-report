"use client";

import { useEffect, useState } from "react";

import { api, type Project } from "@/lib/api";

interface BgOption {
  id: string;
  name: string;
  kind: string;
}

export default function ThemeCard({
  project,
  onSaved,
}: {
  project: Project;
  onSaved: () => Promise<void>;
}) {
  const [backgrounds, setBackgrounds] = useState<BgOption[]>([]);
  const [color, setColor] = useState<string>(
    (project.input_json._theme_color as string) || "#0B6E6B"
  );
  const [bg, setBg] = useState<string>(
    (project.input_json._theme_background as string) || "none"
  );
  const [customName, setCustomName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api<BgOption[]>("/api/backgrounds")
      .then(setBackgrounds)
      .catch(() => {});
  }, []);

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await api(`/api/projects/${project.id}/details`, {
        method: "PUT",
        body: { theme_color: color, theme_background: bg },
      });
      setMessage("Theme saved — regenerate the report to apply it.");
      await onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function uploadCustom(file: File) {
    setMessage("");
    try {
      const form = new FormData();
      form.append("name", "_background");
      form.append("asset_type", "image");
      form.append("file", file);
      await api(`/api/projects/${project.id}/assets`, {
        method: "POST",
        form,
      });
      setBg("custom");
      setCustomName(file.name);
      setMessage("Custom background uploaded — Save, then regenerate.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <div className="card">
      <h2>Report theme</h2>

      <div className="row" style={{ alignItems: "center" }}>
        <div style={{ minWidth: 120 }}>
          <label>Theme color</label>
          <input
            type="color"
            value={/^#[0-9a-fA-F]{6}$/.test(color) ? color : "#0B6E6B"}
            onChange={(e) => setColor(e.target.value)}
            style={{ width: 56, height: 40, padding: 2 }}
            aria-label="Theme color"
          />
        </div>
        <div style={{ minWidth: 140 }}>
          <label>Hex value</label>
          <input
            value={color}
            onChange={(e) => setColor(e.target.value)}
            placeholder="#0B6E6B"
          />
        </div>
        <div style={{ flex: 1 }} />
        <button onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save theme"}
        </button>
      </div>

      <div style={{ marginTop: 14 }}>
        <label>Background template</label>
        <div className="bg-grid">
          {backgrounds.map((option) => (
            <button
              key={option.id}
              type="button"
              className={`bg-swatch ${bg === option.id ? "selected" : ""}`}
              onClick={() => setBg(option.id)}
              title={option.name}
            >
              <img
                src={`/api/backgrounds/${option.id}/preview`}
                alt={option.name}
                loading="lazy"
              />
              <span>{option.name}</span>
            </button>
          ))}
          <button
            type="button"
            className={`bg-swatch ${bg === "custom" ? "selected" : ""}`}
            title={customName || "Upload your own background"}
          >
            <img
              src={customName ? "/api/backgrounds/grad-teal/preview" : "/api/backgrounds/none/preview"}
              alt="Custom"
            />
            <span>{customName || "Custom upload"}</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  uploadCustom(file);
                  setBg("custom");
                }
              }}
              aria-label="Upload custom background"
            />
          </button>
        </div>
      </div>

      {message && <p className="muted">{message}</p>}
    </div>
  );
}