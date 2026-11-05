import { readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ServiceArt } from "@/components/art/service-art";
import { CATEGORY_SCENES, SCENES } from "@/components/art/scenes";

const catalog = readFileSync(join(__dirname, "../../backend/app/catalog_data.py"), "utf8");
const slugs = [...catalog.matchAll(/S\(\("([a-z0-9-]+)", "([a-z0-9-]+)"/g)].map((m) => ({ slug: m[1]!, category: m[2]! }));

describe("service illustrations", () => {
  it("every catalog service has its own illustration", () => {
    expect(slugs.length).toBeGreaterThanOrEqual(90);
    expect(slugs.filter((s) => !SCENES[s.slug]).map((s) => s.slug)).toEqual([]);
  });
  it("every category has a fallback for services added later", () => {
    for (const { category } of slugs) expect(SCENES[CATEGORY_SCENES[category]!]).toBeDefined();
  });
  it("renders an accessible svg", () => {
    const html = renderToStaticMarkup(<ServiceArt slug="printer-setup" category="computer-assistance" title="Printer" />);
    expect(html).toContain('role="img"');
    expect(html).toContain('aria-label="Printer"');
    expect(renderToStaticMarkup(<ServiceArt slug="brand-new" category="graphic-design" />)).toContain("<rect");
  });
});
