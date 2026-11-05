import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWith, router } from "./utils";
import { BackLink } from "@/components/back-link";

describe("service page back button", () => {
  it("opens the category list when the visitor came from outside", () => {
    Object.defineProperty(document, "referrer", { value: "https://google.com/", configurable: true });
    renderWith(<BackLink fallback="/services?category=excel-office" label="Back" />);
    const a = screen.getByRole("link", { name: "Back" });
    expect(a).toHaveAttribute("href", "/services?category=excel-office");
    fireEvent.click(a);
    expect(router.push).toHaveBeenCalledWith("/services?category=excel-office");
  });
  it("returns to the exact previous page (search, filters) when it was on this site", () => {
    Object.defineProperty(document, "referrer", { value: `${window.location.origin}/services?q=win`, configurable: true });
    window.history.pushState({}, "", "/services/windows-install");
    renderWith(<BackLink fallback="/services" label="Back" />);
    fireEvent.click(screen.getByRole("link", { name: "Back" }));
    expect(router.back).toHaveBeenCalled();
  });
});
