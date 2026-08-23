"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Nav from "@/components/Nav";
import TipTapEditor from "@/components/TipTapEditor";
import {
  api,
  AUTH_ENABLED,
  getToken,
  type Generation,
  type Project,
  type Section,
  type Template,
} from "@/lib/api";

const POLL_MS = 2000;

export default function EditPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const pid = params.id;

  const [project, setProject] = useState<Project | null>(null);
  const [schema, setSchema] = useState<Template["schema_json"] | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState("");
  const [rebuilding, setRebuilding] = useState(false);

  useEffect(() => {
    if (AUTH_ENABLED && !getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      const p = await api<Project>(`/api/projects/${pid}`);
      setProject(p);
      const t = await api<Template>(`/api/templates/${p.template_id}/schema`);
      setSchema(t.schema_json);
      const s = await api<Section[]>(`/api/projects/${pid}/sections`);
      setSections(s);
    })().catch((err) => setMessage(err instanceof Error ? err.message : "Load failed"));
  }, [pid, router]);

  function labelFor(key: string) {
    const section = schema?.sections.find((s) => s.key === key);
    return section ? section.label : key;
  }

  async function saveSection(key: string) {
    try {
      await api(`/api/projects/${pid}/sections/${key}`, {
        method: "PUT",
        body: { content_html: drafts[key] ?? "" },
      });
      setSaved((prev) => ({ ...prev, [key]: true }));
      setMessage(`Saved "${labelFor(key)}"`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    }
  }

  async function rebuild() {
    setRebuilding(true);
    setMessage("Rebuilding report from edited sections…");
    try {
      await api(`/api/projects/${pid}/rebuild`, { method: "POST", body: {} });
      const check = setInterval(async () => {
        const g = await api<Generation>(`/api/projects/${pid}/generations/latest`);
        if (g.status === "completed" || g.status === "failed") {
          clearInterval(check);
          setRebuilding(false);
          setMessage(
            g.status === "completed"
              ? "Report rebuilt successfully."
              : `Rebuild failed: ${g.error ?? ""}`
          );
          if (g.status === "completed") router.push(`/projects/${pid}`);
        }
      }, POLL_MS);
    } catch (err) {
      setRebuilding(false);
      setMessage(err instanceof Error ? err.message : "Rebuild failed");
    }
  }

  return (
    <>
      <Nav />
      <div className="container">
        <div className="row">
          <Link href={`/projects/${pid}`}>← Back to project</Link>
          <span className="spacer" />
        </div>
        <h1>Edit report — {project?.title ?? "…"}</h1>

        {message && <p className="muted">{message}</p>}

        {sections.map((section) => (
          <div className="card" key={section.id}>
            <h2>{labelFor(section.section_key)}</h2>
            <TipTapEditor
              initialContent={section.content_html ?? ""}
              onChange={(html) => {
                setDrafts((prev) => ({ ...prev, [section.section_key]: html }));
                setSaved((prev) => ({ ...prev, [section.section_key]: false }));
              }}
            />
            <div className="row" style={{ marginTop: 12 }}>
              <button onClick={() => saveSection(section.section_key)}>
                {saved[section.section_key] ? "✓ Saved" : "Save section"}
              </button>
            </div>
          </div>
        ))}

        <div className="card">
          <h2>Finalize</h2>
          <p className="muted">
            Rebuild the .docx and .pdf with your edited sections folded into the
            template. The original template formatting is preserved.
          </p>
          <button onClick={rebuild} disabled={rebuilding}>
            {rebuilding ? "Rebuilding…" : "Rebuild report"}
          </button>
        </div>
      </div>
    </>
  );
}