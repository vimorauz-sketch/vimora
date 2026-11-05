import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "./utils";
import { mockFetch, renderWith, router } from "./utils";
import { ModeBadge } from "@/components/mode-badge";
import { HandoverPanel, requirementLabel } from "@/features/local/handover";
import { AreaPicker } from "@/features/local/area-picker";
import { OrderForm } from "@/features/order-form";
import en from "@/lib/i18n/en";
import uz from "@/lib/i18n/uz";
import ru from "@/lib/i18n/ru";
import type { OrderDetail, Service } from "@/types/api";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: (k: string) => (k === "vimora_area" && globalThis.__areaCookie ? { value: globalThis.__areaCookie } : undefined) }) }));
const serverGet = vi.fn();
vi.mock("@/lib/server-api", () => ({ serverGet: (...a: unknown[]) => serverGet(...a) }));
vi.mock("@/lib/i18n/server", () => ({ getServerDict: async () => ({ t: en, locale: "en" }) }));
declare global { var __areaCookie: string | undefined }

const AREAS = [
  { slug: "qarapchi", kind: "LOCALITY", name: "Qarapchi village", region: "Jizzax viloyati", district: "Zomin tumani", locality: "Qarapchi", local_services_enabled: true, rules: "" },
  { slug: "zomin-city", kind: "LOCALITY", name: "Zomin town", region: "Jizzax viloyati", district: "Zomin tumani", locality: "Zomin", local_services_enabled: false, rules: "" },
  { slug: "other", kind: "OTHER", name: "Other region (Uzbekistan)", region: "", district: "", locality: "", local_services_enabled: false, rules: "" },
];
const ME = { user: { id: 1, email: "a@example.com", full_name: "A", email_verified: true, is_staff: false, roles: ["CUSTOMER"] }, permissions: [], mfa_pending: false, mfa_enrollment_required: false };

const base: Service = {
  id: 1, slug: "document-printing", category: { id: 2, slug: "printing-local", name: "Printing (Qarapchi)", description: "", icon: "printer" }, name: "Document printing",
  short_description: "Print on A4", icon: "printer", image_url: null, estimated_delivery: "", estimated_hours: null, allows_attachments: true, is_active: true, is_featured: false,
  ai_eligible: false, revision_limit: 2, pricing: { pricing_type: "CUSTOM_QUOTE", currency: "UZS", base_price_minor: 0, unit_label: "", min_quantity: 1, max_quantity: 1000, tiers: [], addons: [], deposit_type: "PERCENT", deposit_value: 0 },
  required_fields: [{ key: "copies", label: "Copies", type: "number", required: true }, { key: "color", label: "Colour", type: "select", required: true, options: ["bw", "color"] }],
  mode: "LOCAL", requires_file: true, availability_status: "ACTIVE", service_area: AREAS[0] as Service["service_area"],
};

function fetchCalled(part: string) {
  return (globalThis.fetch as unknown as { mock?: { calls: unknown[][] } }).mock?.calls.some(([u]) => String(u).includes(part)) ?? false;
}

function setArea(slug: string | null) {
  document.cookie = slug ? `vimora_area=${slug}; path=/` : "vimora_area=; path=/; max-age=0";
}

beforeEach(() => { setArea(null); globalThis.__areaCookie = undefined; });
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

function api(extra?: (url: string, init?: RequestInit) => { status?: number; body?: unknown } | undefined) {
  return mockFetch((url, init) => {
    const x = extra?.(url, init);
    if (x) return x;
    if (url.includes("/auth/me")) return { body: ME };
    if (url.includes("/catalog/areas")) return { body: { items: AREAS } };
    if (url.includes("/public/settings")) return { body: { "uploads.max_mb": 25 } };
    return { status: 404, body: { error: { code: "NOT_FOUND", message: "x" } } };
  });
}

describe("service type badges", () => {
  it("distinguishes online, remote and local services", () => {
    renderWith(<><ModeBadge s={{ ...base, mode: "ONLINE" }} t={en} /><ModeBadge s={{ ...base, mode: "REMOTE" }} t={en} /><ModeBadge s={base} t={en} long /></>);
    expect(screen.getByText(en.biz.modes.ONLINE)).toBeInTheDocument();
    expect(screen.getByText(en.biz.modes.REMOTE)).toBeInTheDocument();
    expect(screen.getByText("In person · only Qarapchi village")).toBeInTheDocument();
  });
  it("is translated in all three languages", () => {
    for (const d of [uz, ru, en]) expect(d.biz.modes.LOCAL && d.biz.notHere.includes("{area}") && d.biz.h.status.READY_FOR_PICKUP).toBeTruthy();
    expect(uz.biz.notHere).toContain("faqat");
  });
});

describe("catalog filters (server page)", () => {
  it("renders the type filters and asks the API for the chosen type", async () => {
    const { default: ServicesPage } = await import("@/app/(public)/services/page");
    serverGet.mockImplementation(async (path: string) => (path.startsWith("/catalog/categories") ? { items: [] } : { items: [{ ...base, mode: "REMOTE", slug: "drivers-install", name: "Driver installation", service_area: null }], total: 1, page: 1 }));
    api();
    renderWith(await ServicesPage({ searchParams: Promise.resolve({ mode: "REMOTE" }) }));
    const nav = screen.getByRole("navigation", { name: en.biz.method });
    for (const k of ["all", "ONLINE", "REMOTE", "LOCAL", "mine"] as const) expect(within(nav).getByText(en.biz.filters[k])).toBeInTheDocument();
    expect(within(nav).getByText(en.biz.filters.REMOTE).closest("a")).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByText(en.biz.filters.LOCAL).closest("a")).toHaveAttribute("href", "/services?mode=LOCAL");
    expect(serverGet.mock.calls.find(([p]) => String(p).startsWith("/catalog/services"))?.[0]).toContain("mode=REMOTE");
    expect(screen.getByText("Driver installation")).toBeInTheDocument();
  });
  it("'available in my area' uses the area the customer chose", async () => {
    const { default: ServicesPage } = await import("@/app/(public)/services/page");
    serverGet.mockImplementation(async (path: string) => (path.startsWith("/catalog/categories") ? { items: [] } : { items: [], total: 0, page: 1 }));
    api();
    globalThis.__areaCookie = "zomin-city";
    renderWith(await ServicesPage({ searchParams: Promise.resolve({ mine: "1" }) }));
    expect(serverGet.mock.calls.find(([p]) => String(p).startsWith("/catalog/services"))?.[0]).toContain("area=zomin-city");
  });
  it("asks for an area when 'my area' is chosen without one", async () => {
    const { default: ServicesPage } = await import("@/app/(public)/services/page");
    serverGet.mockImplementation(async (path: string) => (path.startsWith("/catalog/categories") ? { items: [] } : { items: [], total: 0, page: 1 }));
    api();
    renderWith(await ServicesPage({ searchParams: Promise.resolve({ mine: "1" }) }));
    expect(screen.getByText(en.biz.noAreaForMine)).toBeInTheDocument();
    expect(screen.getByText(en.services.none)).toBeInTheDocument(); // empty state
  });
  it("shows an error state when the catalog cannot load", async () => {
    const { default: ServicesPage } = await import("@/app/(public)/services/page");
    serverGet.mockResolvedValue(null);
    api();
    renderWith(await ServicesPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText(en.common.error)).toBeInTheDocument();
  });
});

describe("area picker", () => {
  it("lists areas and remembers the manual choice (no GPS)", async () => {
    api();
    const geo = vi.fn();
    vi.stubGlobal("navigator", { ...navigator, geolocation: { getCurrentPosition: geo } });
    renderWith(<AreaPicker />);
    const select = await screen.findByRole("combobox", { name: en.biz.chooseArea });
    await waitFor(() => expect(fetchCalled("/catalog/areas")).toBe(true));
    await userEvent.click(select);
    const option = await screen.findByRole("option", { name: /Qarapchi village/ });
    expect(within(option).getByText(en.biz.modes.LOCAL)).toBeInTheDocument(); // local badge in the list
    await userEvent.click(option);
    expect(document.cookie).toContain("vimora_area=qarapchi");
    expect(router.refresh).toHaveBeenCalled();
    expect(geo).not.toHaveBeenCalled();
  });
});

describe("ordering a LOCAL service", () => {
  const next = () => userEvent.click(screen.getByRole("button", { name: new RegExp(`^${en.of.goNext}`) }));

  it("is closed for customers outside Qarapchi", async () => {
    setArea("zomin-city");
    const fetch = api();
    renderWith(<OrderForm service={base} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("only in Qarapchi village");
    expect(screen.getByRole("button", { name: new RegExp(`^${en.of.goNext}`) })).toBeDisabled();
    expect(screen.queryByText(en.of.short.handover)).not.toBeInTheDocument(); // no handover step outside the area
    expect(fetch.mock.calls.some(([u, i]) => String(u).endsWith("/api/v1/orders") && i?.method === "POST")).toBe(false);
  });

  it("walks through the steps one at a time, offers pickup/meetup in Qarapchi and sends the choice", async () => {
    setArea("qarapchi");
    let sent: Record<string, unknown> | null = null;
    api((url, init) => {
      if (url.endsWith("/api/v1/files") && init?.method === "POST") return { status: 201, body: { id: 9, name: "a.pdf", mime_type: "application/pdf", size_bytes: 10, purpose: "ORDER_INPUT", scan_status: "CLEAN", created_at: "" } };
      if (url.endsWith("/api/v1/orders") && init?.method === "POST") { sent = JSON.parse(String(init.body)); return { status: 201, body: { id: 77 } }; }
      return undefined;
    });
    renderWith(<OrderForm service={base} />);
    // step 1: area — only this step is visible
    expect(await screen.findByText("Step 1 of 5")).toBeInTheDocument();
    expect(screen.queryByLabelText(en.of.descLabel)).not.toBeInTheDocument();
    await next();
    // step 2: the task; empty description blocks moving on
    expect(await screen.findByLabelText(en.of.descLabel)).toBeInTheDocument();
    await next();
    expect(await screen.findByText(en.of.fixStep)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Copies"), "2");
    await userEvent.click(screen.getByRole("combobox", { name: "Colour" }));
    await userEvent.click(await screen.findByRole("option", { name: en.biz.opt.color })); // friendly label for the "color" value
    await userEvent.type(screen.getByLabelText(en.of.descLabel), "Please print my 20 page essay");
    await next();
    // step 3: handover
    expect(await screen.findByText(en.biz.pickup)).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText(new RegExp(en.biz.meetup)));
    await userEvent.type(screen.getByLabelText(en.biz.meetupPlace), "By the school");
    const when = new Date(Date.now() + 2 * 86400_000);
    const local = new Date(when.getTime() - when.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    await userEvent.type(screen.getByLabelText(en.biz.meetupTime), local);
    await next();
    // step 4: files — a file is required for printing
    expect(await screen.findByText("Step 4 of 5")).toBeInTheDocument();
    await next();
    expect(await screen.findByText(en.biz.requiresFile)).toBeInTheDocument();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, new File(["%PDF-1.4"], "a.pdf", { type: "application/pdf" }));
    await waitFor(() => expect(screen.getByText("a.pdf")).toBeInTheDocument());
    await next();
    // step 5: review and send
    await userEvent.click(await screen.findByRole("button", { name: en.services.placeOrder }));
    await waitFor(() => expect(sent).not.toBeNull());
    expect(sent).toMatchObject({ service_slug: "document-printing", title: "Document printing", area: "qarapchi", handover_method: "MEETUP", meetup_place: "By the school", attachment_ids: [9], requirements: { copies: "2", color: "color" } });
    expect(router.push).toHaveBeenCalledWith("/dashboard/orders/77");
  });

  it("requires choosing an area first", async () => {
    let posted = false;
    api((url, init) => { if (url.endsWith("/api/v1/orders") && init?.method === "POST") { posted = true; return { status: 201, body: { id: 1 } }; } return undefined; });
    renderWith(<OrderForm service={{ ...base, mode: "ONLINE", slug: "translation", service_area: null, requires_file: false, required_fields: [] }} />);
    expect(await screen.findByText("Step 1 of 4")).toBeInTheDocument();
    await next();
    expect(await screen.findByText(en.biz.chooseArea, { selector: "p.text-danger" })).toBeInTheDocument();
    expect(screen.getByText("Step 1 of 4")).toBeInTheDocument();
    expect(posted).toBe(false);
  });
});

describe("handover panel", () => {
  const order = (h: Partial<NonNullable<OrderDetail["handover"]>>, extra: Partial<OrderDetail> = {}) => ({
    id: 5, status: "READY_FOR_DELIVERY", remaining_minor: 0, handover: { method: "PICKUP", status: "READY_FOR_PICKUP", proposal: null, agreed: null, handed_over_at: null, pickup_address: null, ...h }, ...extra,
  }) as unknown as OrderDetail;

  it("shows the pickup address only when the server provides it", () => {
    const { unmount } = renderWith(<HandoverPanel order={order({ pickup_address: "Qarapchi, 17" })} onDone={() => {}} />);
    expect(screen.getByText("Qarapchi, 17")).toBeInTheDocument();
    expect(screen.getByText(en.biz.h.status.READY_FOR_PICKUP)).toBeInTheDocument();
    unmount();
    renderWith(<HandoverPanel order={order({ status: "WAITING" })} onDone={() => {}} />);
    expect(screen.queryByText(en.biz.h.address)).not.toBeInTheDocument();
  });
  it("lets the customer accept the owner's meetup proposal", async () => {
    const fetch = api((url, init) => (url.includes("/handover/accept") && init?.method === "POST" ? { body: {} } : undefined));
    const done = vi.fn();
    renderWith(<HandoverPanel order={order({ method: "MEETUP", status: "PROPOSED_BY_ADMIN", proposal: { place: "Guzar", time: new Date(Date.now() + 86400_000).toISOString(), note: "", by: "admin", at: "" } })} onDone={done} />);
    expect(screen.getByText("Guzar")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: en.biz.h.accept }));
    await waitFor(() => expect(done).toHaveBeenCalled());
    expect(fetch.mock.calls.some(([u]) => String(u).includes("/orders/5/handover/accept"))).toBe(true);
  });
  it("translates printing requirements", () => {
    expect(requirementLabel(uz, "color", "bw")).toEqual(["Rang", "Oq-qora"]);
    expect(requirementLabel(ru, "copies", "3")).toEqual(["Копий", "3"]);
  });
});

describe("mobile layout", () => {
  it("filter chips scroll horizontally instead of wrapping off-screen", async () => {
    const { default: ServicesPage } = await import("@/app/(public)/services/page");
    serverGet.mockImplementation(async (path: string) => (path.startsWith("/catalog/categories") ? { items: [] } : { items: [], total: 0, page: 1 }));
    api();
    renderWith(await ServicesPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("navigation", { name: en.biz.method }).className).toContain("overflow-x-auto");
  });
});

describe("catalog search box", () => {
  const cats = [
    { id: 1, slug: "computer-assistance", name: "Computer help", description: "", icon: "monitor-cog", service_count: 10 },
    { id: 2, slug: "printing-local", name: "Printing (Qarapchi)", description: "", icon: "printer", service_count: 4 },
    { id: 3, slug: "empty", name: "Nothing here", description: "", icon: "sparkles", service_count: 0 },
  ];
  it("shows all categories as soon as it is focused", async () => {
    api();
    const { SearchBox } = await import("@/features/catalog/search-box");
    renderWith(<SearchBox cats={cats} />);
    await userEvent.click(screen.getByRole("combobox", { name: en.common.search }));
    const box = screen.getByRole("listbox");
    expect(within(box).getByText("Computer help")).toBeInTheDocument();
    expect(within(box).getByText("Printing (Qarapchi)")).toBeInTheDocument();
    expect(within(box).queryByText("Nothing here")).not.toBeInTheDocument();
  });
  it("searches live from the first letter and opens the chosen result with the keyboard", async () => {
    api((url) => url.includes("/catalog/services?") ? { body: { items: [{ ...base, slug: "windows-install", name: "Windows setup", category: cats[0] }], total: 1, page: 1, page_size: 6 } } : undefined);
    const { SearchBox } = await import("@/features/catalog/search-box");
    renderWith(<SearchBox cats={cats} />);
    const input = screen.getByRole("combobox", { name: en.common.search });
    await userEvent.type(input, "W");
    expect(await screen.findByRole("option", { name: /Windows setup/ })).toBeInTheDocument();
    expect(fetchCalled("q=W")).toBe(true);
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(router.push).toHaveBeenCalledWith("/services/windows-install");
  });
});
