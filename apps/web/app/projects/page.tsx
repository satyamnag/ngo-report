"use client";

import Nav from "@/components/Nav";
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
              <select
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
              >
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} (v{t.version})
                  </option>
                ))}
              </select>
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
            </div>
          </div>
        ))}
      </div>
    </>
  );
}