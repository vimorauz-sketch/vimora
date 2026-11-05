"use client";

import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { Me, SiteSettings } from "@/types/api";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try { return await api<Me>("/auth/me"); } catch (e) { if (e instanceof ApiError && e.status === 401) return null; throw e; }
    },
    staleTime: 60_000,
  });
}

export function useSite() {
  return useQuery({ queryKey: ["site"], queryFn: () => api<SiteSettings>("/site"), staleTime: 300_000 });
}
