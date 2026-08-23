"use client";

import { useCallback, useEffect, useState } from "react";

import { api, type Project } from "@/lib/api";

interface Doc {
  id: string;
  name: string;
  original_name: string | null;
  content_type: string;
  has_text: boolean;
  created_at: string;
}

const ACCEPT =
  ".txt,.pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.gif";

export default function DocumentsCard({ project }: { project: Project }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const list = await api<Doc[]>(`/api/projects/${project.id}/documents`);
      setDocs(list);
    } catch {
      /* ignore */
    }
  }, [project.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function upload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setBusy(true);
    setMessage("");
    const file = files[0];
    try {
      const form = new FormData();
      form.append("file", file);
      await api(`/api/projects/${project.id}/documents`, {
        method: "POST",
        form,
      });
      setMessage(`Uploaded ${file.name}.`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Research documents</h2>
      <p className="muted">
        Attach txt, Word, Excel, PowerPoint, PDF, or images. The agent reads
        them to build your report.
      </p>
      <input
        type="file"
        accept={ACCEPT}
        disabled={busy}
        onChange={(e) => upload(e.target.files)}
      />
      {docs.length > 0 && (
        <ul style={{ paddingLeft: 18, margin: "10px 0" }}>
          {docs.map((d) => (
            <li key={d.id} className="muted">
              {d.original_name || d.name}{" "}
              {!d.has_text && " (image — stored, no extractable text)"}
            </li>
          ))}
        </ul>
      )}
      {message && <p className="muted">{message}</p>}
    </div>
  );
}