import { NextResponse, type NextRequest } from "next/server";

/** Fast redirect for signed-out visitors. Real authorization is always enforced by the API. */
export function middleware(req: NextRequest) {
  if (!req.cookies.get("vimora_session")) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(req.nextUrl.pathname + req.nextUrl.search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/dashboard/:path*", "/admin/:path*"] };
