import "server-only";

const INTERNAL = process.env.INTERNAL_API_URL || "http://127.0.0.1:8000";

/** Server-side fetch for public data (SSR). Returns null on failure so pages degrade gracefully. */
export async function serverGet<T>(path: string, { revalidate = 60 }: { revalidate?: number | false } = {}): Promise<T | null> {
  try {
    const res = await fetch(`${INTERNAL}/api/v1${path}`, { next: revalidate === false ? undefined : { revalidate }, cache: revalidate === false ? "no-store" : undefined });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
