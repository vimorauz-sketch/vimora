import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, errorMessage } from "@/lib/api";
import en from "@/lib/i18n/en";
import uz from "@/lib/i18n/uz";
import ru from "@/lib/i18n/ru";
import { safeNext } from "@/features/auth/forms";

vi.mock("next/navigation", () => ({ useRouter: () => ({}), useSearchParams: () => new URLSearchParams(), usePathname: () => "/" }));

afterEach(() => { vi.unstubAllGlobals(); document.cookie = "vimora_csrf=; max-age=0"; });

describe("api client", () => {
  it("sends the CSRF cookie value as a header on writes, never on reads", async () => {
    document.cookie = "vimora_csrf=tok123";
    const calls: RequestInit[] = [];
    vi.stubGlobal("fetch", vi.fn(async (_u: string, init: RequestInit) => { calls.push(init); return new Response("{}", { status: 200 }); }));
    await api("/orders");
    await api("/orders", { body: { a: 1 } });
    expect((calls[0]!.headers as Record<string, string>)["X-CSRF-Token"]).toBeUndefined();
    expect((calls[1]!.headers as Record<string, string>)["X-CSRF-Token"]).toBe("tok123");
    expect(calls[1]!.credentials).toBe("same-origin");
  });
  it("maps the error envelope to ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: { code: "RATE_LIMITED", message: "x" } }), { status: 429 })));
    const e = (await api("/x").catch((x: unknown) => x)) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.code).toBe("RATE_LIMITED");
    expect(errorMessage(e, en)).toContain(en.errors.RATE_LIMITED);
  });
  it("reports network failures clearly", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fail"); }));
    const e = (await api("/x").catch((x: unknown) => x)) as ApiError;
    expect(errorMessage(e, en)).toContain(en.errors.network);
  });
});

describe("post-login redirect", () => {
  it("only allows same-site relative paths", () => {
    expect(safeNext("/dashboard/orders/1")).toBe("/dashboard/orders/1");
    expect(safeNext("https://evil.example")).toBe("/dashboard");
    expect(safeNext("//evil.example")).toBe("/dashboard");
    expect(safeNext("/\\evil.example")).toBe("/dashboard");
    expect(safeNext(null)).toBe("/dashboard");
  });
});

describe("friendly server errors", () => {
  it("never shows raw proxy text like 'Internal Server Error'", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("Internal Server Error", { status: 500, statusText: "Internal Server Error" })));
    const e = await api("/auth/login", { body: {} }).catch((x: unknown) => x);
    expect(errorMessage(e, en)).toContain(en.errors.SERVER_ERROR);
  });
  it("maps gateway errors to 'temporarily unavailable'", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("Bad Gateway", { status: 502 })));
    const e = await api("/x").catch((x: unknown) => x);
    expect(errorMessage(e, en)).toContain(en.errors.SERVER_UNAVAILABLE);
  });
  it("localizes the backend's internal error envelope", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: { code: "INTERNAL_ERROR", message: "An unexpected error occurred" } }), { status: 500 })));
    const e = await api("/x").catch((x: unknown) => x);
    expect(errorMessage(e, en)).toContain(en.errors.SERVER_ERROR);
  });
});


function mockFetch(h: () => { status: number; body: unknown }) {
  vi.stubGlobal("fetch", vi.fn(async () => { const r = h(); return new Response(JSON.stringify(r.body), { status: r.status }); }));
}

describe("error codes shown to users", () => {
  it("adds the error number and code to every message", async () => {
    mockFetch(() => ({ status: 400, body: { error: { code: "SERVICE_NOT_IN_AREA", number: "E7003", message: "x", request_id: "abc" } } }));
    const e = await api("/orders", { body: {} }).catch((x) => x);
    expect(errorMessage(e, en)).toBe(`${en.errors.SERVICE_NOT_IN_AREA} (${en.errorInfo.label}: E7003 · SERVICE_NOT_IN_AREA)`);
    expect(errorMessage(e, uz)).toContain("Xato kodi: E7003");
  });
  it("explains which field failed validation and why, in the user's language", async () => {
    mockFetch(() => ({ status: 422, body: { error: { code: "VALIDATION_ERROR", number: "E1001", message: "Request validation failed",
      details: [{ loc: ["body", "description"], field: "description", type: "string_too_short", ctx: { min_length: 10 } }, { loc: ["body", "contact_phone"], field: "contact_phone", type: "string_too_long", ctx: { max_length: 40 } }] } } }));
    const e = await api("/orders", { body: {} }).catch((x) => x);
    const m = errorMessage(e, uz);
    expect(m).toContain("«Tavsif» — kamida 10 ta belgi bo'lsin");
    expect(m).toContain("«Telefon» — ko'pi bilan 40 ta belgi bo'lsin");
    expect(m).toContain("E1001 · VALIDATION_ERROR");
    expect(m).not.toContain("Request validation failed");
  });
  it("shows a short request id for server errors so support can find them", async () => {
    mockFetch(() => ({ status: 500, body: { error: { code: "INTERNAL_ERROR", number: "E1012", message: "boom", request_id: "1234567890abcdef" } } }));
    const e = await api("/x").catch((x) => x);
    expect(errorMessage(e, ru)).toBe(`${ru.errors.SERVER_ERROR} (${ru.errorInfo.label}: E1012 · INTERNAL_ERROR · ID 12345678)`);
  });
  it("has a translated explanation for every backend error code", async () => {
    const fs = await import("node:fs");
    const path = await import("node:path");
    const src = fs.readFileSync(path.join(__dirname, "../../backend/app/core/errors.py"), "utf8");
    const codes = [...src.matchAll(/\d{4}: "([A-Z_]+)"/g)].map((m) => m[1]!);
    expect(codes.length).toBeGreaterThan(100);
    for (const d of [uz, en, ru]) expect(codes.filter((c) => !d.errors[c as keyof typeof d.errors])).toEqual([]);
  });
});

describe("password errors", () => {
  it("are translated rule by rule, with the error code", async () => {
    mockFetch(() => ({ status: 400, body: { error: { code: "WEAK_PASSWORD", number: "E1103", message: "x", details: ["classes", "too_short"] } } }));
    const e = await api("/auth/register", { body: {} }).catch((x) => x);
    const m = errorMessage(e, uz);
    expect(m).toContain(uz.auth.pw.classes);
    expect(m).toContain(uz.auth.pw.too_short);
    expect(m).toContain("E1103 · WEAK_PASSWORD");
    expect(m).not.toMatch(/Password must/);
  });
});
