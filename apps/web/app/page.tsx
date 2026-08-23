"use client";

import Nav from "@/components/Nav";
import TemplatePreview from "@/components/TemplatePreview";
import { api, type Project, type Template } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const ACCEPT = ".txt,.pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.gif";

export default function HomePage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api<Template[]>("/api/templates")
      .then((list) => {
        setTemplates(list);
        if (list[0]) setTemplateId(list[0].id);
      })
      .catch(() => {});
  }, []);

  async function generate() {
    setError("");
    setBusy(true);
    try {
      if (!templateId) throw new Error("Choose a template");
      const project = await api<Project>("/api/projects", {
        method: "POST",
        body: { template_id: templateId, title: title || "Annual Report" },
      });

      if (prompt.trim()) {
        await api(`/api/projects/${project.id}/details`, {
          method: "PUT",
          body: { input_json: { _user_prompt: prompt.trim() } },
        });
      }

      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        await api(`/api/projects/${project.id}/documents`, {
          method: "POST",
          form,
        });
      }

      await api(`/api/projects/${project.id}/research-generate`, {
        method: "POST",
        body: {},
      });

      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
      setBusy(false);
    }
  }

  return (
    <>
      <Nav />
      <div className="home">
        <h1>Build Reports Smarter with AI</h1>
        <p className="home-sub">
          Describe your annual report, attach documents, and the AI agent will
          research and draft it for you.
        </p>

        <div className="home-card">
          <div className="row">
            <div style={{ flex: 1 }}>
              <label htmlFor="home-template">Template</label>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <select
                  id="home-template"
                  style={{ flex: 1 }}
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                >
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} (v{t.version})
                    </option>
                  ))}
                </select>
                <TemplatePreview templateId={templateId} />
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="home-title">Report Title</label>
              <input
                id="home-title"
                value={title}
                placeholder="e.g. 2026 Annual Report"
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
          </div>

          <label htmlFor="home-prompt" style={{ marginTop: 14 }}>
            Describe your report
          </label>
          <div className="prompt-box">
            <textarea
              id="home-prompt"
              rows={4}
              value={prompt}
              placeholder="Tell the agent what to cover — e.g. our 2026 impact, the three new programmes, and our donor acknowledgment…"
              onChange={(e) => setPrompt(e.target.value)}
            />
            <div className="prompt-footer">
              <button
                type="button"
                className="attach-btn"
                title="Attach documents (txt, Word, Excel, PowerPoint, PDF, images)"
                onClick={() => fileInput.current?.click()}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                </svg>
                <span>Attach</span>
              </button>
              <input
                ref={fileInput}
                type="file"
                multiple
                accept={ACCEPT}
                style={{ display: "none" }}
                onChange={(e) => {
                  const picked = Array.from(e.target.files ?? []);
                  setFiles((prev) => [...prev, ...picked]);
                  e.target.value = "";
                }}
              />
              <button onClick={generate} disabled={busy || !templateId}>
                {busy ? "Generating…" : "Generate"}
              </button>
            </div>
          </div>

          {files.length > 0 && (
            <div className="file-list">
              {files.map((f, i) => (
                <span key={`${f.name}-${i}`}>
                  📎 {f.name}
                  <button
                    type="button"
                    className="danger"
                    title="Remove"
                    onClick={() => setFiles((prev) => prev.filter((_, idx) => idx !== i))}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          {error && <p className="error">{error}</p>}
          <p className="muted" style={{ marginTop: 10 }}>
            <strong>Your data is 100% safe.</strong> Documents are stored on
            your own server, used only to build your report, and never shared.
          </p>
        </div>
      </div>
    </>
  );
}