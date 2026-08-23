"use client";

import { useCallback, useEffect, useState } from "react";

import { api, type Project } from "@/lib/api";

const PLATFORMS: { key: string; label: string; hint: string }[] = [
  { key: "website", label: "Official website", hint: "https://yourorg.org" },
  { key: "facebook", label: "Facebook page", hint: "https://facebook.com/yourorg" },
  { key: "instagram", label: "Instagram page", hint: "https://instagram.com/yourorg" },
  { key: "twitter", label: "X / Twitter", hint: "https://x.com/yourorg" },
  { key: "linkedin", label: "LinkedIn page", hint: "https://linkedin.com/company/yourorg" },
  { key: "youtube", label: "YouTube channel", hint: "https://youtube.com/@yourorg" },
];

interface Source {
  platform: string;
  url: string | null;
  status: string;
  error: string | null;
  fetched_chars: number | null;
}

export default function SourcesCard({ project }: { project: Project }) {
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [sources, setSources] = useState<Source[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const list = await api<Source[]>(`/api/projects/${project.id}/sources`);
      setSources(list);
      const map: Record<string, string> = {};
      for (const s of list) if (s.url) map[s.platform] = s.url;
      setUrls((prev) => ({ ...prev, ...map }));
    } catch {
      /* ignore */
    }
  }, [project.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await api(`/api/projects/${project.id}/sources`, {
        method: "PUT",
        body: urls,
      });
      setMessage("Sources saved — granting the agent read access.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function fetchAll() {
    setBusy(true);
    setMessage("Fetching sources…");
    try {
      const list = await api<Source[]>(`/api/projects/${project.id}/sources/fetch`, {
        method: "POST",
        body: {},
      });
      setSources(list);
      const ok = list.filter((s) => s.status === "ok").length;
      setMessage(`Fetched ${ok}/${list.filter((s) => s.url).length} sources.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Fetch failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Grant the agent read access</h2>
      <p className="muted">
        Enter your official website and social pages. The agent reads them
        read-only (public pages only) to gather this year&apos;s data.
      </p>
      {PLATFORMS.map((p) => {
        const status = sources.find((s) => s.platform === p.key);
        return (
          <div key={p.key}>
            <label htmlFor={`src-${p.key}`}>{p.label}</label>
            <div className="row">
              <div style={{ flex: 1 }}>
                <input
                  id={`src-${p.key}`}
                  value={urls[p.key] ?? ""}
                  placeholder={p.hint}
                  onChange={(e) =>
                    setUrls((prev) => ({ ...prev, [p.key]: e.target.value }))
                  }
                />
              </div>
              {status && status.url && (
                <span className={`status-pill ${status.status}`}>
                  {status.status === "ok"
                    ? `${status.fetched_chars ?? 0} chars`
                    : status.status}
                </span>
              )}
            </div>
            {status?.error && <p className="error">{status.error}</p>}
          </div>
        );
      })}
      <div className="row" style={{ marginTop: 12 }}>
        <button onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save sources"}
        </button>
        <button className="secondary" onClick={fetchAll} disabled={busy}>
          Fetch source content
        </button>
      </div>
      {message && <p className="muted">{message}</p>}
    </div>
  );
}