import ReactMarkdown from "react-markdown";
import { date } from "@/lib/format";
import { getServerDict } from "@/lib/i18n/server";
import { serverGet } from "@/lib/server-api";

type Page = { published: boolean; title: string | null; body: string | null; updated_at?: string };

/** Owner-authored content. Markdown is rendered without raw HTML (react-markdown default), so no XSS. */
export async function PolicyPage({ slug, fallbackTitle }: { slug: string; fallbackTitle: (t: Awaited<ReturnType<typeof getServerDict>>["t"]) => string }) {
  const { t, locale } = await getServerDict();
  const p = await serverGet<Page>(`/pages/${slug}?lang=${locale}`, { revalidate: 120 });
  return (
    <article className="mx-auto max-w-[860px] px-5 py-14 sm:px-8">
      <h1 className="display text-[32px] sm:text-[44px]">{p?.title || fallbackTitle(t)}</h1>
      {p?.published && p.body ? (
        <>
          {p.updated_at && <p className="mt-3 text-[13px] text-muted">{t.pages.updated.replace("{date}", date(p.updated_at, locale))}</p>}
          <div className="prose-vimora mt-10"><ReactMarkdown skipHtml>{p.body}</ReactMarkdown></div>
        </>
      ) : (
        <p className="mt-8 text-muted">{t.pages.notPublished}</p>
      )}
    </article>
  );
}
