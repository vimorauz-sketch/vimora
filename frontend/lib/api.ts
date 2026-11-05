/**
 * Browser API client. Auth is a HttpOnly session cookie the JS cannot read; state-changing
 * requests echo the readable CSRF cookie in X-CSRF-Token. No tokens are kept in localStorage.
 */
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown, public number?: string, public requestId?: string) {
    super(message);
  }
}

function csrf(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const m = document.cookie.match(/(?:^|;\s*)vimora_csrf=([^;]+)/);
  return m?.[1] ? decodeURIComponent(m[1]) : undefined;
}

type Opts = { method?: string; body?: unknown; headers?: Record<string, string>; form?: FormData; signal?: AbortSignal };

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const method = opts.method ?? (opts.body !== undefined || opts.form ? "POST" : "GET");
  const headers: Record<string, string> = { ...opts.headers };
  if (method !== "GET") {
    const token = csrf();
    if (token) headers["X-CSRF-Token"] = token;
  }
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  let res: Response;
  try {
    res = await fetch(`/api/v1${path}`, { method, headers, body, credentials: "same-origin", signal: opts.signal, cache: "no-store" });
  } catch {
    throw new ApiError(0, "NETWORK", "network");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = data?.error;
    if (!err) {
      // Not our JSON envelope (proxy/gateway/crash page): never show raw text like "Internal Server Error".
      const code = res.status >= 502 && res.status <= 504 ? "SERVER_UNAVAILABLE" : res.status >= 500 ? "SERVER_ERROR" : "HTTP_ERROR";
      throw new ApiError(res.status, code, res.statusText, undefined, `E0${res.status}`, res.headers.get("X-Request-ID") ?? undefined);
    }
    throw new ApiError(res.status, err.code ?? "HTTP_ERROR", err.message ?? res.statusText, err.details, err.number, err.request_id ?? res.headers.get("X-Request-ID") ?? undefined);
  }
  return data as T;
}

type ErrDict = { errors: Record<string, string>; errorInfo?: { fields: Record<string, string>; types: Record<string, string>; label: string }; auth?: { pw?: Record<string, string>; pwPrefix?: string } };
type FieldIssue = { field?: string | null; loc?: string[]; type?: string; ctx?: Record<string, string | number> };

/** "«Description» — must be at least 10 characters" for each invalid field (max 4). */
export function validationIssues(details: unknown, t: ErrDict): string[] {
  if (!Array.isArray(details)) return [];
  const info = t.errorInfo;
  return (details as FieldIssue[]).slice(0, 4).map((d) => {
    const path = d.field ?? (d.loc ?? []).filter((p) => !["body", "query", "path", "header"].includes(p)).join(".");
    const leaf = path.split(".").filter((p) => !/^\d+$/.test(p)).pop() ?? path;
    const name = info?.fields[path] ?? info?.fields[leaf] ?? (leaf || "?");
    let reason = info?.types[d.type ?? ""] ?? info?.types.default ?? d.type ?? "";
    Object.entries(d.ctx ?? {}).forEach(([k, v]) => { reason = reason.replace(`{${k}}`, String(v)); });
    return `«${name}» — ${reason}`;
  });
}

/** Localized explanation of an error, always ending with its number and code, e.g. "… (Xato kodi: E7003 · SERVICE_NOT_IN_AREA)". */
export function errorMessage(e: unknown, t: ErrDict): string {
  const label = t.errorInfo?.label ?? "Error code";
  if (!(e instanceof ApiError)) return `${t.errors.SERVER_ERROR ?? (e instanceof Error ? e.message : String(e))} (${label}: E0000 · CLIENT_ERROR)`;
  let text: string;
  if (e.code === "NETWORK") text = t.errors.network ?? e.message;
  else if (e.code === "WEAK_PASSWORD" && Array.isArray(e.details)) {
    const rules = (e.details as string[]).map((r) => t.auth?.pw?.[r] ?? r);
    text = `${t.auth?.pwPrefix ?? t.errors.WEAK_PASSWORD ?? ""} ${rules.join("; ")}.`;
  }
  else if (e.code === "SERVER_UNAVAILABLE") text = t.errors.SERVER_UNAVAILABLE ?? e.message;
  else if (e.status >= 500 || e.code === "INTERNAL_ERROR" || e.code === "SERVER_ERROR") text = t.errors.SERVER_ERROR ?? e.message;
  else if (e.code === "VALIDATION_ERROR") {
    const issues = validationIssues(e.details, t);
    text = `${t.errors.VALIDATION_ERROR ?? e.message}${issues.length ? ` ${issues.join("; ")}.` : ""}`;
  } else if (e.code === "HTTP_ERROR") text = t.errors.HTTP_ERROR ?? t.errors.SERVER_ERROR ?? e.message;
  else text = t.errors[e.code] ?? e.message;
  const num = e.number ?? (e.code === "NETWORK" ? "E0000" : e.status ? `E0${e.status}` : "E0000");
  const rid = e.requestId && e.status >= 500 ? ` · ID ${e.requestId.slice(0, 8)}` : "";
  return `${text} (${label}: ${num} · ${e.code}${rid})`;
}
