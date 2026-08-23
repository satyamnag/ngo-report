"use client";

import Nav from "@/components/Nav";
import ConfirmDialog from "@/components/ConfirmDialog";
import TemplatePreview from "@/components/TemplatePreview";
import { api, AUTH_ENABLED, getToken, type Project, type Template } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function ProjectsPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const [toDelete, setToDelete] = useState<Project | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (AUTH_ENABLED && !getToken()) {
      router.replace("/login");
      return;
    }
    api<Template[]>("/api/templates")
      .then((list) => {
        setTemplates(list);
        if (list[0]) setTemplateId(list[0].id);
      })
      .catch(() => {});
    api<Project[]>("/api/projects").then(setProjects).catch(() => {});
  }, [router]);

  async function create() {
    setError("");
    try {
      const project = await api<Project>("/api/projects", {
        method: "POST",
        body: { template_id: templateId, title },
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function confirmDelete() {
    if (!toDelete) return;
    setDeleting(true);
    setError("");
    try {
      await api(`/api/projects/${toDelete.id}`, { method: "DELETE" });
      setProjects((prev) => prev.filter((p) => p.id !== toDelete.id));
      setToDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      setToDelete(null);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <Nav />
      <div className="container">
        <h1>Projects</h1>

        <div className="card">
          <h2>New report</h2>
          <div className="row">
            <div style={{ flex: 1 }}>
              <label>Template</label>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <select
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
              <label>Report title</label>
              <input
                value={title}
                placeholder="e.g. 2025 Annual Report"
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
          </div>
          {error && <p className="error">{error}</p>}
          <div className="row" style={{ marginTop: 14 }}>
            <button onClick={create}>Create project</button>
          </div>
        </div>

        {projects.length === 0 && <p className="muted">No projects yet.</p>}
        {projects.map((p) => (
          <div className="card" key={p.id}>
            <div className="row">
              <div>
                <strong>{p.title}</strong>
                <div className="muted">
                  updated {new Date(p.updated_at).toLocaleString()}
                </div>
              </div>
              <span className="spacer" />
              <span className={`status-pill ${p.status}`}>{p.status}</span>
              <a href={`/projects/${p.id}`}>Open →</a>
              <button className="danger" onClick={() => setToDelete(p)}>
                Delete
              </button>
            </div>
          </div>
        ))}

        <ConfirmDialog
          open={!!toDelete}
          title="Delete this report?"
          message={`This permanently deletes "${toDelete?.title ?? "this report"}" and its generated files. This cannot be undone.`}
          confirmLabel={deleting ? "Deleting…" : "Delete"}
          onConfirm={confirmDelete}
          onCancel={() => setToDelete(null)}
        />
      </div>
    </>
  );
}