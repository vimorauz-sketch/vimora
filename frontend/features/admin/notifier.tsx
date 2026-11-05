"use client";

import { useQuery } from "@tanstack/react-query";
import { Bell, BellRing, Play, Volume2, VolumeX, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Switch } from "@/components/ui/misc";
import { useMe } from "@/hooks/queries";
import { api } from "@/lib/api";
import { cn, date } from "@/lib/format";
import { useI18n } from "@/lib/i18n/client";
import { kindFor, playSound, type SoundKind, type SoundStyle, soundReady, unlockSound } from "@/lib/sound";

type Item = { id: number; event_type: string; title: string; order_number: string | null; lines: [string, string][]; link: string; created_at: string };
type Feed = { items: Item[]; latest_id: number };
type Prefs = { sound: boolean; volume: number; style: SoundStyle; desktop: boolean };

const DEFAULT_PREFS: Prefs = { sound: true, volume: 0.7, style: "bells", desktop: false };
const PRIORITY: SoundKind[] = ["payment", "order", "alert", "message", "soft"];

function load<T>(key: string, fallback: T): T {
  try { const v = localStorage.getItem(key); return v ? { ...fallback, ...JSON.parse(v) } : fallback; } catch { return fallback; }
}
function loadNum(key: string): number {
  try { return Number(localStorage.getItem(key) || 0) || 0; } catch { return 0; }
}
function saveNum(key: string, n: number) {
  try { localStorage.setItem(key, String(n)); } catch { /* storage unavailable */ }
}

/** Admin bell: polls the staff activity feed, plays a melody for new events, shows a list. */
export function AdminNotifier() {
  const { t, locale } = useI18n();
  const n = t.admin.notif;
  const { data: me } = useMe();
  const uid = me?.user.id ?? 0;
  const keys = { prefs: "vimora_admin_sound", seen: `vimora_admin_seen_${uid}`, announced: `vimora_admin_announced_${uid}` };
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT_PREFS);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Item[]>([]);
  const [seen, setSeen] = useState(0);
  const [locked, setLocked] = useState(false);
  const [toast, setToast] = useState<Item | null>(null);
  const latest = useRef(0);
  const started = useRef(false);
  const baseTitle = useRef("");
  const enabled = !!me?.permissions.includes("orders.view");

  useEffect(() => { setPrefs(load(keys.prefs, DEFAULT_PREFS)); setSeen(loadNum(keys.seen)); }, [keys.prefs, keys.seen]);
  const update = (p: Partial<Prefs>) => setPrefs((old) => {
    const next = { ...old, ...p };
    try { localStorage.setItem(keys.prefs, JSON.stringify(next)); } catch { /* ignore */ }
    return next;
  });

  // browsers only allow sound after the user interacts with the page once
  useEffect(() => {
    const unlock = () => { void unlockSound().then((ok) => setLocked(!ok)); };
    window.addEventListener("pointerdown", unlock, { once: false, passive: true });
    window.addEventListener("keydown", unlock);
    return () => { window.removeEventListener("pointerdown", unlock); window.removeEventListener("keydown", unlock); };
  }, []);

  const feed = useQuery({
    queryKey: ["admin-activity", uid],
    queryFn: () => api<Feed>(`/admin/activity?after_id=${latest.current}`),
    enabled,
    refetchInterval: 8000,
    refetchIntervalInBackground: true,
  });

  const announce = useCallback((fresh: Item[]) => {
    const announced = loadNum(keys.announced);
    const news = fresh.filter((i) => i.id > announced);
    const top = news[0];
    if (!top) return;
    saveNum(keys.announced, Math.max(...news.map((i) => i.id))); // other open tabs will not repeat it
    const kinds = news.map((i) => kindFor(i.event_type)).filter(Boolean) as SoundKind[];
    const kind = PRIORITY.find((k) => kinds.includes(k));
    if (prefs.sound && kind) {
      const played = playSound(kind, prefs.style, prefs.volume);
      if (!played) setLocked(true);
    }
    setToast(top);
    if (prefs.desktop && typeof Notification !== "undefined" && Notification.permission === "granted" && document.hidden) {
      const note = new Notification(`VIMORA — ${n.events[top.event_type as keyof typeof n.events] ?? top.title}`, { body: top.order_number ? `#${top.order_number}` : "", tag: `vimora-${top.id}` });
      note.onclick = () => { window.focus(); window.location.href = top.link; };
    }
  }, [keys.announced, prefs, n.events]);

  useEffect(() => {
    const d = feed.data;
    if (!d) return;
    const first = !started.current;
    started.current = true;
    if (d.items.length) setItems((old) => [...d.items, ...old.filter((o) => !d.items.some((x) => x.id === o.id))].slice(0, 40));
    if (first) {
      // first load: nothing is "new" yet, just remember where we are
      if (!loadNum(keys.announced)) saveNum(keys.announced, d.latest_id);
      if (!loadNum(keys.seen)) { saveNum(keys.seen, d.latest_id); setSeen(d.latest_id); }
    } else if (d.items.length) {
      announce(d.items);
    }
    latest.current = Math.max(latest.current, d.latest_id);
  }, [feed.data, announce, keys.announced, keys.seen]);

  useEffect(() => { if (!toast) return; const h = setTimeout(() => setToast(null), 7000); return () => clearTimeout(h); }, [toast]);

  const unread = items.filter((i) => i.id > seen).length;
  useEffect(() => {
    if (!baseTitle.current) baseTitle.current = document.title.replace(/^\(\d+\)\s*/, "");
    document.title = unread ? `(${unread}) ${baseTitle.current}` : baseTitle.current;
  }, [unread]);

  function markSeen() {
    const top = items[0]?.id ?? seen;
    setSeen(top);
    saveNum(keys.seen, top);
  }
  async function test(kind: SoundKind) {
    await unlockSound();
    setLocked(!soundReady());
    playSound(kind, prefs.style, prefs.volume);
  }
  async function askDesktop(on: boolean) {
    if (on && typeof Notification !== "undefined" && Notification.permission !== "granted") {
      const r = await Notification.requestPermission().catch(() => "denied" as NotificationPermission);
      if (r !== "granted") return update({ desktop: false });
    }
    update({ desktop: on });
  }

  if (!enabled) return null;
  const label = (i: Item) => n.events[i.event_type as keyof typeof n.events] ?? i.title;

  return (
    <>
      {toast && !open && (
        <Link href={toast.link} onClick={() => setToast(null)}
          className="card fixed bottom-24 right-5 z-50 flex w-[320px] items-start gap-3 p-4 shadow-[var(--shadow-lift)] animate-[vimora-pop_.35s_ease-out]">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-tint-0 text-accent"><BellRing className="h-4 w-4" /></span>
          <span className="min-w-0 flex-1">
            <span className="block text-[14px] font-semibold text-ink">{label(toast)}</span>
            {toast.order_number && <span className="block text-[13px] text-muted">#{toast.order_number}</span>}
          </span>
          <button type="button" aria-label={n.close} onClick={(e) => { e.preventDefault(); setToast(null); }} className="text-muted hover:text-fg"><X className="h-4 w-4" /></button>
        </Link>
      )}

      <button type="button" onClick={() => { setOpen(!open); void unlockSound().then((ok) => setLocked(!ok)); }} aria-expanded={open} aria-label={`${n.title}${unread ? ` (${unread})` : ""}`}
        className={cn("fixed bottom-5 right-5 z-50 grid h-14 w-14 place-items-center rounded-full bg-ink text-ink-fg shadow-[var(--shadow-lift)] transition-transform hover:scale-105", unread > 0 && "animate-[vimora-ring_1.6s_ease-in-out_infinite]")}>
        {unread ? <BellRing className="h-5 w-5" /> : <Bell className="h-5 w-5" />}
        {unread > 0 && <span className="absolute -right-0.5 -top-0.5 min-w-[22px] rounded-full bg-accent px-1.5 py-0.5 text-center text-[11.5px] font-semibold text-accent-fg tabular-nums">{unread > 9 ? "9+" : unread}</span>}
        {prefs.sound && locked && <span className="absolute -bottom-1 -left-1 grid h-5 w-5 place-items-center rounded-full bg-warn text-white" title={n.locked}><VolumeX className="h-3 w-3" /></span>}
      </button>

      {open && (
        <div role="dialog" aria-label={n.title} className="card fixed bottom-24 right-5 z-50 flex max-h-[min(640px,calc(100dvh-120px))] w-[min(380px,calc(100vw-40px))] flex-col overflow-hidden shadow-[var(--shadow-lift)]">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <p className="font-[family-name:var(--font-display)] text-[18px] text-ink">{n.title}</p>
            <div className="flex items-center gap-1">
              {unread > 0 && <button type="button" onClick={markSeen} className="rounded-full px-2.5 py-1 text-[12.5px] text-accent hover:bg-raised">{n.markRead}</button>}
              <button type="button" onClick={() => setOpen(false)} aria-label={n.close} className="rounded-full p-1.5 text-muted hover:bg-raised"><X className="h-4 w-4" /></button>
            </div>
          </div>

          {prefs.sound && locked && (
            <button type="button" onClick={() => test("message")} className="mx-4 mt-3 rounded-[12px] bg-tint-5 px-3 py-2 text-left text-[13px] text-fg">{n.locked}</button>
          )}

          <ul className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
            {items.length === 0 && <li className="px-3 py-8 text-center text-[14px] text-muted">{n.empty}</li>}
            {items.map((i) => (
              <li key={i.id}>
                <Link href={i.link} onClick={() => setOpen(false)} className="flex gap-3 rounded-[12px] px-3 py-2.5 hover:bg-raised">
                  <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", i.id > seen ? "bg-accent" : "bg-transparent")} />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[14px] font-medium text-ink">{label(i)}</span>
                    <span className="block truncate text-[12.5px] text-muted">{[i.order_number && `#${i.order_number}`, date(i.created_at, locale, true)].filter(Boolean).join(" · ")}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>

          <div className="space-y-2 border-t border-border bg-raised/40 px-4 py-3">
            <Switch label={<span className="flex items-center gap-2">{prefs.sound ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}{n.sound}</span>} checked={prefs.sound} onCheckedChange={(v) => update({ sound: v })} />
            {prefs.sound && (
              <>
                <label className="flex items-center gap-3 text-[13px] text-muted">
                  <span className="w-20 shrink-0">{n.volume}</span>
                  <input type="range" min={0.1} max={1} step={0.05} value={prefs.volume} onChange={(e) => update({ volume: Number(e.target.value) })} className="w-full accent-[var(--accent)]" />
                </label>
                <div className="flex items-center gap-3 text-[13px] text-muted">
                  <span className="w-20 shrink-0">{n.style}</span>
                  <div className="flex flex-wrap gap-1">
                    {(["bells", "marimba", "harp"] as SoundStyle[]).map((s) => (
                      <button key={s} type="button" onClick={() => { update({ style: s }); void unlockSound().then(() => playSound("order", s, prefs.volume)); }} aria-pressed={prefs.style === s}
                        className={cn("rounded-full border px-3 py-1 text-[12.5px] transition-colors", prefs.style === s ? "border-accent bg-accent text-accent-fg" : "border-border bg-surface text-fg hover:border-accent/60")}>
                        {n.styles[s]}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-3 text-[13px] text-muted">
                  <span className="w-20 shrink-0">{n.listen}</span>
                  <div className="flex flex-wrap gap-1">
                    {(["order", "payment", "message", "alert"] as SoundKind[]).map((k) => (
                      <button key={k} type="button" onClick={() => test(k)} className="inline-flex items-center gap-1 rounded-full border border-border bg-surface px-2.5 py-1 text-[12.5px] text-fg hover:border-accent/60">
                        <Play className="h-3 w-3" />{n.kinds[k]}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
            <Switch label={n.desktop} checked={prefs.desktop} onCheckedChange={(v) => void askDesktop(v)} />
          </div>
        </div>
      )}
    </>
  );
}
