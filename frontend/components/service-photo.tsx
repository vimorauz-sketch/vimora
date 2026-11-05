"use client";

import { useState } from "react";
import { ServiceArt } from "@/components/art/service-art";
import { cn } from "@/lib/format";

/** Service cover: the admin's own photo if one was uploaded, otherwise the service's illustration. */
export function ServicePhoto({ src, slug, category, alt = "", className, eager = false }: {
  src?: string | null; slug: string; category?: string; alt?: string; className?: string; eager?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return <ServiceArt slug={slug} category={category} title={alt} className={cn("block rounded-[12px]", className)} />;
  }
  return (
    <img src={src} alt={alt} loading={eager ? "eager" : "lazy"} decoding="async" referrerPolicy="no-referrer"
      onError={() => setFailed(true)} className={cn("rounded-[12px] bg-raised object-cover", className)} />
  );
}
