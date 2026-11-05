/** @type {import('next').NextConfig} */
const INTERNAL_API = process.env.INTERNAL_API_URL || "http://127.0.0.1:8000";
const isProd = process.env.NODE_ENV === "production";

// CSP: no inline scripts from third parties, no framing, API calls only to self.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isProd ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://images.unsplash.com https://unsplash.com",
  "font-src 'self'",
  `connect-src 'self'${isProd ? "" : " ws: http://127.0.0.1:8000"}`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self' https://my.click.uz https://checkout.paycom.uz https://checkout.stripe.com",
].join("; ");

const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    // Same-origin API: in production Caddy routes /api straight to FastAPI (incl. WebSockets);
    // this rewrite is the fallback when the Next server is reached directly (dev, local tests).
    return [{ source: "/api/:path*", destination: `${INTERNAL_API}/api/:path*` }];
  },
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Content-Security-Policy", value: csp },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    }];
  },
};
export default nextConfig;
