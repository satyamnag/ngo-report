"use client";

import { useEffect, useState } from "react";

import { api, type Template } from "@/lib/api";

function setPath(root: Record<string, unknown>, path: string, value: unknown) {
  const keys = path.split(".");
  let node = root;
  for (const key of keys.slice(0, -1)) {
    const next = node[key];
    if (next && typeof next === "object") {
      node = next as Record<string, unknown>;
    } else {
      const child: Record<string, unknown> = {};
      node[key] = child;
      node = child;
    }
  }
  node[keys[keys.length - 1]] = value;
}

export default function DynamicForm({
  schema,
  initial,
  projectId,
  onSave,
}: {
  schema: Template["schema_json"];
  initial?: Record<string, unknown>;
  projectId: string;
  onSave: (inputJson: Record<string, unknown>) => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [uploaded, setUploaded] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    // Flatten nested input_json into dot-paths keyed by field name.
    const flat: Record<string, string> = {};
    for (const group of schema.fields) {
      for (const field of group.fields) {
        let node: unknown = initial ?? {};
        for (const key of field.path.split(".")) {
          if (node && typeof node === "object") {
            node = (node as Record<string, unknown>)[key];
          } else {
            node = undefined;
            break;
          }
        }
        if (node !== undefined && node !== null) {
          flat[field.name] = String(node);
        }
      }
    }
    setValues(flat);
  }, [schema, initial]);

  async function handleImageUpload(
    field: { name: string; label: string; placeholder?: string },
    file: File
  ) {
    setBusy(true);
    setMessage("");
    try {
      const form = new FormData();
      form.append("name", field.placeholder || field.name);
      form.append("asset_type", "image");
      form.append("file", file);
      await api(`/api/projects/${projectId}/assets`, {
        method: "POST",
        form,
      });
      setUploaded((prev) => ({
        ...prev,
        [field.name]: file.name,
      }));
      setMessage(`Uploaded ${file.name} for "${field.placeholder || field.name}"`);
    } catch (err) {
      setMessage(
        err instanceof Error ? `Upload failed: ${err.message}` : "Upload failed"
      );
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setSaving(true);
    setMessage("");
    try {
      const inputJson: Record<string, unknown> = {};
      for (const group of schema.fields) {
        for (const field of group.fields) {
          if (field.type === "image") continue;
          const value = values[field.name];
          if (value !== undefined && value !== "") {
            setPath(inputJson, field.path, field.type === "number" ? Number(value) : value);
          }
        }
      }
      await onSave(inputJson);
      setMessage("Details saved");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      {schema.fields.map((group) => (
        <div className="field-group" key={group.group}>
          <h3>{group.group}</h3>
          {group.fields.map((field) => {
            if (field.type === "image") {
              return (
                <div key={field.name}>
                  <label>
                    {field.label}{" "}
                    {uploaded[field.name] && (
                      <span className="muted">✓ {uploaded[field.name]}</span>
                    )}
                  </label>
                  <div className="uploads">
                    <div className="upload-card">
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp,image/gif"
                        disabled={busy}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleImageUpload(field, file);
                        }}
                      />
                    </div>
                  </div>
                </div>
              );
            }
            const common = {
              id: field.name,
              value: values[field.name] ?? "",
              onChange: (e: { target: { value: string } }) =>
                setValues((prev) => ({ ...prev, [field.name]: e.target.value })),
            };
            return (
              <div key={field.name}>
                <label htmlFor={field.name}>
                  {field.label}
                  {field.required && " *"}
                </label>
                {field.type === "textarea" ? (
                  <textarea
                    {...common}
                    rows={3}
                    style={{ fontFamily: "inherit" }}
                  />
                ) : (
                  <input
                    {...common}
                    type={field.type === "number" ? "number" : "text"}
                  />
                )}
              </div>
            );
          })}
        </div>
      ))}
      {message && <p className={message.includes("failed") ? "error" : "muted"}>{message}</p>}
      <button disabled={saving} onClick={save}>
        {saving ? "Saving…" : "Save details"}
      </button>
    </div>
  );
}