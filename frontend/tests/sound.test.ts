import { describe, expect, it } from "vitest";
import { MELODIES, kindFor } from "@/lib/sound";

describe("admin notification sounds", () => {
  it("maps events to a melody", () => {
    expect(kindFor("order.created")).toBe("order");
    expect(kindFor("custom_request.created")).toBe("order");
    expect(kindFor("payment.deposit_received")).toBe("payment");
    expect(kindFor("payment.final_received")).toBe("payment");
    expect(kindFor("payment.failed")).toBe("alert");
    expect(kindFor("message.received")).toBe("message");
    expect(kindFor("ai.started")).toBeNull();
    expect(kindFor("something.else")).toBe("soft");
  });
  it("melodies use audible, correctly tuned notes", () => {
    for (const notes of Object.values(MELODIES)) {
      expect(notes.length).toBeGreaterThan(0);
      for (const n of notes) expect(n.f).toBeGreaterThan(300), expect(n.f).toBeLessThan(3200);
    }
    // A6 = 1760 Hz
    expect(MELODIES.soft[0]!.f).toBeCloseTo(1760, 0);
  });
});
