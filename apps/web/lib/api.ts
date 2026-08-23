// API is proxied same-origin (/api/* -> FastAPI backend via next.config rewrites),
// so browsers never hit mixed-content blocks. No absolute backend URL needed.
export const API_URL = "";

// Auth is disabled until Clerk is integrated: pages no longer require login.
export const AUTH_ENABLED = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export async function api<T = unknown>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    form?: FormData;
    token?: string | null;
    raw?: boolean;
  } = {}
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = options.token !== undefined ? options.token : getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const res = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") || "";
  return (contentType.includes("application/json")
    ? res.json()
    : res) as T;
}

export async function downloadFile(
  path: string,
  filename: string
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ---------- types ----------

export interface Template {
  id: string;
  name: string;
  description: string | null;
  status: string;
  version: number;
  schema_json: {
    sections: { key: string; label: string; sort: number }[];
    section_map: Record<string, string>;
    fields: {
      group: string;
      fields: {
        name: string;
        label: string;
        type: string;
        path: string;
        placeholder?: string;
        required?: boolean;
      }[];
    }[];
  };
}

export interface Project {
  id: string;
  title: string;
  status: string;
  template_id: string;
  input_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Generation {
  id: string;
  project_id: string;
  status: string;
  error: string | null;
  output_docx_key: string | null;
  output_pdf_key: string | null;
  created_at: string;
}

export interface Section {
  id: string;
  section_key: string;
  content_html: string | null;
  image_url: string | null;
  sort_order: number;
}

export interface Asset {
  id: string;
  name: string;
  asset_type: string;
  original_name: string | null;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  org_name: string;
  role: string;
}