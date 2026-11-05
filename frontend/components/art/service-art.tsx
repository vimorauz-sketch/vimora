import { CATEGORY_SCENES, SCENES } from "./scenes";

const CATEGORY_TINT: Record<string, number> = {
  "computer-assistance": 2, "documents-pdf": 0, "excel-office": 1, "text-translation": 4, "graphic-design": 3, "image-processing": 5,
  "video-audio": 0, "smm-social-media": 3, "web-development": 2, "telegram-automation": 2, "software-development": 1, "data-processing": 5,
  "hosting-deployment": 4, "api-integration": 1, "ai-services": 4, "online-services": 0, "lessons-consulting": 5, "custom-digital-tasks": 3, "printing-local": 0,
};

export function hasArt(slug: string, category?: string): boolean {
  return !!SCENES[slug] || !!(category && CATEGORY_SCENES[category]);
}

/** Hand-drawn illustration for a service (falls back to its category's scene). */
export function ServiceArt({ slug, category, title, className }: { slug: string; category?: string; title?: string; className?: string }) {
  const scene = SCENES[slug] ?? (category ? SCENES[CATEGORY_SCENES[category] ?? ""] : undefined);
  const tint = category ? CATEGORY_TINT[category] ?? 0 : 0;
  return (
    <svg viewBox="0 0 320 200" className={className} role="img" aria-label={title} preserveAspectRatio="xMidYMid slice">
      <rect width="320" height="200" fill={`var(--art-${tint})`} />
      <circle cx="292" cy="22" r="58" fill="var(--art-dot)" />
      <circle cx="18" cy="188" r="46" fill="var(--art-dot)" />
      <ellipse cx="160" cy="184" rx="120" ry="8" fill="#000" opacity="0.05" />
      {scene ? scene() : null}
    </svg>
  );
}
