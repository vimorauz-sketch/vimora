import { describe, expect, it } from "vitest";
import { date, fromMinor, money, toMinor } from "@/lib/format";
import { pctOf } from "@/lib/money";

describe("money formatting (integer minor units, no float drift)", () => {
  it("formats UZS per locale", () => {
    expect(money(150_000_000, "UZS", "uz")).toBe("1 500 000 so'm");
    expect(money(150_000_000, "UZS", "ru")).toBe("1 500 000 сум");
    expect(money(150_000_000, "UZS", "en")).toBe("1,500,000 UZS");
    expect(money(1999, "USD", "en")).toBe("$19.99");
    expect(money(null, "UZS")).toBe("—");
  });
  it("parses user input to minor units exactly", () => {
    expect(toMinor("150 000")).toBe(15_000_000);
    expect(toMinor("19.99")).toBe(1999);
    expect(toMinor("0,1")).toBe(10);
    expect(toMinor("0.1")! + toMinor("0.2")!).toBe(30);
    expect(toMinor("abc")).toBeNull();
    expect(toMinor("1.234")).toBeNull();
    expect(fromMinor(1999)).toBe("19.99");
    expect(fromMinor(15_000_000)).toBe("150000");
  });
  it("mirrors backend deposit rounding", () => {
    expect(pctOf(10_000_000, 30, "UZS")).toBe(3_000_000);
    expect(pctOf(10_051, 30, "UZS")).toBe(3100);
    expect(pctOf(333, 50, "USD")).toBe(167);
  });
});

describe("uzbek dates", () => {
  it("does not rely on missing ICU data", () => {
    expect(date("2026-11-02T10:05:00Z", "uz")).toMatch(/^2-noyabr, 2026$/);
  });
});
