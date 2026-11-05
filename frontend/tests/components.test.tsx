import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import "./utils";
import { mockFetch, renderWith, router, setPath } from "./utils";
import { StageRail, StatusBadge } from "@/components/domain";
import { LoginForm, RegisterForm } from "@/features/auth/forms";
import { AppShell } from "@/components/layout/app-shell";
import en from "@/lib/i18n/en";
import uz from "@/lib/i18n/uz";
import ru from "@/lib/i18n/ru";

afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

describe("translations", () => {
  it("uz and ru define every key en defines", () => {
    const keys = (o: object, p = ""): string[] => Object.entries(o).flatMap(([k, v]) => (v && typeof v === "object" && !Array.isArray(v) ? keys(v, `${p}${k}.`) : [`${p}${k}`]));
    expect(keys(uz).sort()).toEqual(keys(en).sort());
    expect(keys(ru).sort()).toEqual(keys(en).sort());
  });
});

describe("status display", () => {
  it("highlights customer actions and marks the current stage", () => {
    renderWith(<><StatusBadge status="DEPOSIT_PENDING" /><StageRail status="DEPOSIT_PENDING" /></>);
    expect(screen.getByText(en.status.DEPOSIT_PENDING)).toBeInTheDocument();
    const current = document.querySelector('[aria-current="step"]');
    expect(current?.textContent).toBe(en.stage[2]);
  });
  it("shows no progress for cancelled orders", () => {
    renderWith(<StageRail status="CANCELLED" />);
    expect(document.querySelector('[aria-current="step"]')).toBeNull();
  });
});

describe("login form", () => {
  it("shows a generic error for bad credentials", async () => {
    mockFetch(() => ({ status: 401, body: { error: { code: "INVALID_CREDENTIALS", message: "Invalid email or password" } } }));
    renderWith(<LoginForm />);
    await userEvent.type(screen.getByLabelText(en.auth.email), "a@example.com");
    await userEvent.type(screen.getByLabelText(en.auth.password), "wrong-password");
    fireEvent.click(screen.getByRole("button", { name: en.auth.signInTitle }));
    expect(await screen.findByText(en.auth.invalid)).toBeInTheDocument();
  });
  it("switches to the MFA step when required", async () => {
    mockFetch((url) => (url.includes("/auth/login") ? { body: { mfa_required: true } } : { status: 404 }));
    renderWith(<LoginForm />);
    await userEvent.type(screen.getByLabelText(en.auth.email), "a@example.com");
    await userEvent.type(screen.getByLabelText(en.auth.password), "secret-pass");
    fireEvent.click(screen.getByRole("button", { name: en.auth.signInTitle }));
    expect(await screen.findByLabelText(en.auth.code)).toBeInTheDocument();
  });
});

describe("register form validation", () => {
  it("blocks submission until fields are valid and terms accepted", async () => {
    const f = mockFetch(() => ({ status: 201, body: { email_delivery: "PENDING" } }));
    renderWith(<RegisterForm />);
    fireEvent.click(screen.getByRole("button", { name: en.nav.signUp }));
    expect(await screen.findByText(en.auth.passwordRules, { selector: "p[role=alert]" })).toBeInTheDocument();
    expect(f).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText(en.auth.fullName), "Aziz");
    await userEvent.type(screen.getByLabelText(en.auth.email), "aziz@example.com");
    await userEvent.type(screen.getByLabelText(en.auth.password), "Str0ng!Password");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: en.nav.signUp }));
    expect(await screen.findByText(en.auth.registered)).toBeInTheDocument();
    const body = JSON.parse((f.mock.calls.at(-1)![1] as RequestInit).body as string);
    expect(body).toMatchObject({ email: "aziz@example.com", accept_terms: true });
  });
  it("tells the user when email delivery is not configured", async () => {
    mockFetch(() => ({ status: 201, body: { email_delivery: "NOT_CONFIGURED" } }));
    renderWith(<RegisterForm />);
    await userEvent.type(screen.getByLabelText(en.auth.fullName), "Aziz");
    await userEvent.type(screen.getByLabelText(en.auth.email), "aziz@example.com");
    await userEvent.type(screen.getByLabelText(en.auth.password), "Str0ng!Password");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: en.nav.signUp }));
    expect(await screen.findByText((c) => c.includes(en.auth.emailNotConfigured) && c.includes("E1116 · EMAIL_NOT_CONFIGURED"))).toBeInTheDocument();
  });
  it("shows the verification link only when the local server returns one", async () => {
    mockFetch(() => ({ status: 201, body: { email_delivery: "PENDING", dev_verify_url: "http://localhost:3001/verify-email?token=abc" } }));
    renderWith(<RegisterForm />);
    await userEvent.type(screen.getByLabelText(en.auth.fullName), "Aziz");
    await userEvent.type(screen.getByLabelText(en.auth.email), "aziz@example.com");
    await userEvent.type(screen.getByLabelText(en.auth.password), "Str0ng!Password");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: en.nav.signUp }));
    expect(await screen.findByRole("link", { name: en.auth.devVerifyBtn })).toHaveAttribute("href", "/verify-email?token=abc");
  });
  it("checks the password rules live and blocks a weak password before sending", async () => {
    const fetch = mockFetch(() => ({ status: 201, body: { email_delivery: "PENDING" } }));
    renderWith(<RegisterForm />);
    await userEvent.type(screen.getByLabelText(en.auth.password), "abcdefghij");
    expect(screen.getByText(en.auth.pwCheck.len).closest("li")).toHaveClass("text-ok");
    expect(screen.getByText(en.auth.pwCheck.upper).closest("li")).toHaveClass("text-muted");
    await userEvent.type(screen.getByLabelText(en.auth.fullName), "Aziz");
    await userEvent.type(screen.getByLabelText(en.auth.email), "aziz@example.com");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: en.nav.signUp }));
    expect(await screen.findByText(en.auth.passwordRules)).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });
});

const me = (staff: boolean) => ({ user: { id: 1, email: "u@example.com", full_name: "U", roles: staff ? ["ADMIN"] : ["CUSTOMER"], is_staff: staff, email_verified: true, mfa_enabled: false, notification_prefs: {} }, mfa_pending: false, mfa_enrollment_required: false, permissions: [] });

describe("app shell access control", () => {
  it("redirects customers away from the admin panel", async () => {
    setPath("/admin");
    mockFetch(() => ({ body: me(false) }));
    renderWith(<AppShell nav={[]} home="/admin" requireStaff><p>secret admin</p></AppShell>);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/dashboard"));
    expect(screen.queryByText("secret admin")).toBeNull();
  });
  it("redirects signed-out visitors to login with a return path", async () => {
    setPath("/dashboard/orders");
    mockFetch(() => ({ status: 401, body: { error: { code: "UNAUTHORIZED", message: "x" } } }));
    renderWith(<AppShell nav={[]} home="/dashboard"><p>private</p></AppShell>);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login?next=%2Fdashboard%2Forders"));
  });
  it("renders for staff", async () => {
    setPath("/admin");
    mockFetch(() => ({ body: me(true) }));
    renderWith(<AppShell nav={[{ href: "/admin", label: "Overview", icon: null }]} home="/admin" requireStaff><p>admin content</p></AppShell>);
    expect(await screen.findByText("admin content")).toBeInTheDocument();
  });
});

describe("password field", () => {
  it("can show and hide what was typed", async () => {
    const { PasswordInput } = await import("@/components/ui/password-input");
    renderWith(<label>Parol<PasswordInput /></label>);
    const input = screen.getByLabelText("Parol", { selector: "input" });
    await userEvent.type(input, "Secret-123");
    expect(input).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: en.auth.showPassword }));
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveValue("Secret-123");
    await userEvent.click(screen.getByRole("button", { name: en.auth.hidePassword }));
    expect(input).toHaveAttribute("type", "password");
  });
});
