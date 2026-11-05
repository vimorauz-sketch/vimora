import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockFetch, renderWith, router } from "./utils";
import { CustomOrderForm } from "@/features/custom-order";
import en from "@/lib/i18n/en";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<object>()), useSearchParams: () => new URLSearchParams() }));
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });
const ME = { user: { id: 1, email: "a@example.com", full_name: "A", phone: "+998901112233", email_verified: true, is_staff: false, roles: ["CUSTOMER"] }, permissions: [], mfa_pending: false, mfa_enrollment_required: false };
const cats = [{ id: 1, slug: "excel-office", name: "Excel & Office", description: "", icon: "sheet", service_count: 5 }];

describe("custom request wizard", () => {
  it("goes step by step, validates and sends one request", async () => {
    let sent: Record<string, unknown> | null = null;
    mockFetch((url, init) => {
      if (url.includes("/auth/me")) return { body: ME };
      if (url.includes("/public/settings")) return { body: { "uploads.max_mb": 25 } };
      if (url.endsWith("/api/v1/orders") && init?.method === "POST") { sent = JSON.parse(String(init.body)); return { status: 201, body: { id: 9 } }; }
      return { status: 404, body: { error: { code: "NOT_FOUND", message: "x" } } };
    });
    renderWith(<CustomOrderForm categories={cats} />);
    const next = () => userEvent.click(screen.getByRole("button", { name: new RegExp(`^${en.of.goNext}`) }));
    expect(await screen.findByText("Step 1 of 4")).toBeInTheDocument();
    await next();
    expect(await screen.findByText(en.custom.minLength)).toBeInTheDocument(); // empty task cannot move on
    await userEvent.click(screen.getByRole("combobox", { name: en.co.catLabel }));
    await userEvent.click(await screen.findByRole("option", { name: /Excel & Office/ }));
    await userEvent.type(screen.getByLabelText(en.custom.taskTitle), "Price calculator");
    await userEvent.type(screen.getByLabelText(en.custom.description), "An Excel file that adds 20% margin to every product price.");
    await next();
    await userEvent.click(screen.getByRole("radio", { name: en.of.whenOpts.d3 }));
    await userEvent.click(screen.getByRole("radio", { name: /500k/ }));
    await next();
    expect(screen.getByLabelText(new RegExp(en.co.phone))).toHaveValue("+998901112233"); // prefilled from the profile
    await userEvent.type(screen.getByLabelText(new RegExp(en.co.telegram)), "@my_shop");
    await next();
    expect(screen.getByText("Price calculator")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: en.custom.submit }));
    await waitFor(() => expect(sent).not.toBeNull());
    expect(sent).toMatchObject({ title: "Price calculator", category_slug: "excel-office", budget_minor: 500_000_00, contact_phone: "+998901112233", contact_telegram: "@my_shop", preferred_language: "en" });
    expect(typeof (sent as unknown as { deadline: string }).deadline).toBe("string");
    expect(router.push).toHaveBeenCalledWith("/dashboard/orders/9");
  });
});
