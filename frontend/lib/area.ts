"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Area } from "@/types/api";

export const AREA_COOKIE = "vimora_area";
const EVENT = "vimora-area-change";

function readCookie(): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(/(?:^|;\s*)vimora_area=([a-z0-9-]{1,80})/);
  return m ? m[1]! : null;
}

/** The customer's area, chosen by hand (no GPS). Kept in a cookie so server pages can filter by it. */
export function useArea() {
  const [area, setAreaState] = useState<string | null>(null);
  useEffect(() => {
    setAreaState(readCookie());
    const on = () => setAreaState(readCookie());
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, []);
  const setArea = useCallback((slug: string | null) => {
    document.cookie = slug ? `${AREA_COOKIE}=${slug}; path=/; max-age=31536000; samesite=lax` : `${AREA_COOKIE}=; path=/; max-age=0; samesite=lax`;
    setAreaState(slug);
    window.dispatchEvent(new Event(EVENT));
  }, []);
  return { area, setArea };
}

export function useAreas(locale: string) {
  return useQuery({ queryKey: ["areas", locale], queryFn: () => api<{ items: Area[] }>(`/catalog/areas?lang=${locale}`), staleTime: 300_000 });
}
