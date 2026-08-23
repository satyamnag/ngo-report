"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import DynamicForm from "@/components/DynamicForm";
import Nav from "@/components/Nav";
import {
  api,
  downloadFile,
  getToken,
  type Generation,
  type Project,
  type Template,
} from "@/lib/api";

const POLL_MS = 2000;

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const pid = params.id;

  const [project, setProject] = useState<Project | null>(null);
  const [template, setTemplate] = useState<Template | null>(null);
  const [generation, setGeneration] = useState<Generation | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiMessage, setAiMessage] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function refresh() {
    const p = await api<Project>(`/api/projects/${pid}`);
    setProject(p);
    const t = await api<Template>(`/api/templates/${p.template_id}/schema`);
    setTemplate(t);
    try {
      const g = await api<Generation>(`/api/projects/${pid}/generations/latest`);
      setGeneration(g);
    } catch {
      setGeneration(null);
    }
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    refresh().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pid]);

  function pollUntilDone() {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const g = await api<Generation>(`/api/projects/${pid}/generations/latest`);
        setGeneration(g);
        if (g.status === "completed" || g.status === "failed") {
          stopPolling();
          refresh().catch(() => {});
        }
      } catch {
        stopPolling();
      }
    }, POLL_MS);
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => stopPolling, []);

  async function generate() {
    setError("");
    setBusy(true);
    try {
      await api(`/api/projects/${pid}/generate`, { method: "POST", body: {} });
      pollUntilDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveDetails(inputJson: Record<string, unknown>) {
    await api(`/api/projects/${pid}/details`, {
      method: "PUT",
      body: { input_json: inputJson },
    });
    refresh();
  }

  async function aiGenerate() {
    setError("");
    setAiBusy(true);
    setAiMessage("");
    try {
      const res = await api<{ applied: boolean }>(`/api/projects/${pid}/ai-generate`, {
        method: "POST",
        body: {},
      });
      setAiMessage(res.applied ? "AI content plan applied — review and save below." : "AI generation completed.");
      await refresh();
    } catch (err) {
      setAiMessage(err instanceof Error ? err.message : "AI generation failed");
    } finally {
      setAiBusy(false);
    }
  }

  async function showPreview() {
    const res = await api<Response>(`/api/projects/${pid}/report`, { raw: true });
    const html = await res.text();
    const url = URL.createObjectURL(
      new Blob([html], { type: "text/html" })
    );
    setPreviewUrl(url);
  }

  const running = generation && ["pending", "running", "converting"].includes(generation.status);

  return (
    <>
      <Nav />
      <div className="container">
        <div className="row">
          <Link href="/projects">← Projects</Link>
          <span className="spacer" />
          <Link href={`/projects/${pid}/edit`}>Edit sections (TipTap) →</Link>
        </div>

        <h1>{project?.title ?? "Loading…"}</h1>

        {error && <p className="error">{error}</p>}

        {template && project && (
          <>
            <div className="card">
              <h2>Report details</h2>
              <div className="row" style={{ marginBottom: 8 }}>
                <button className="secondary" onClick={aiGenerate} disabled={aiBusy}>
                  {aiBusy ? "Generating with AI…" : "Auto-fill with AI"}
                </button>
                {aiMessage && (
                  <span className={aiMessage.includes("failed") || aiMessage.includes("not configured") ? "error" : "muted"}>
                    {aiMessage}
                  </span>
                )}
              </div>
              <DynamicForm
                schema={template.schema_json}
                initial={project.input_json}
                projectId={pid}
                onSave={saveDetails}
              />
            </div>

            <div className="card">
              <h2>Generate &amp; download</h2>
              <div className="row">
                <button onClick={generate} disabled={busy || !!running}>
                  {running ? "Generating…" : busy ? "Starting…" : "Generate report"}
                </button>
                {generation && (
                  <span className={`status-pill ${generation.status}`}>
                    {generation.status}
                    {running ? "…" : ""}
                  </span>
                )}
              </div>
              {generation?.error && (
                <p className="error">Generation error: {generation.error}</p>
              )}
              {generation?.status === "completed" && (
                <div className="row" style={{ marginTop: 14 }}>
                  <button
                    className="secondary"
                    onClick={() => downloadFile(`/api/projects/${pid}/download?format=docx`, `${project.title}.docx`)}
                  >
                    Download .docx
                  </button>
                  <button
                    className="secondary"
                    onClick={() => downloadFile(`/api/projects/${pid}/download?format=pdf`, `${project.title}.pdf`)}
                  >
                    Download .pdf
                  </button>
                  <button className="secondary" onClick={showPreview}>
                    Preview HTML
                  </button>
                </div>
              )}
            </div>

            {previewUrl && (
              <div className="card">
                <h2>Preview</h2>
                <iframe
                  src={previewUrl}
                  style={{ width: "100%", height: 700, border: "1px solid var(--border)", borderRadius: 8 }}
                  title="Report preview"
                />
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}