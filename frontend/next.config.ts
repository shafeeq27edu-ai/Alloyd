import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

function toOrigin(value: string | undefined): string {
  if (!value) return "";
  try {
    return new URL(value).origin;
  } catch {
    return "";
  }
}

const apiOrigin =
  toOrigin(process.env.NEXT_PUBLIC_API_BASE_URL) || (isProd ? "" : "http://localhost:8000");

const cspHeader = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isProd ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  `connect-src 'self'${apiOrigin ? ` ${apiOrigin}` : ""}`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "object-src 'none'",
  "form-action 'self'",
].join("; ");

const nextConfig: NextConfig = {
  async headers() {
    const headersList = [
      {
        key: 'Content-Security-Policy',
        value: cspHeader,
      },
      {
        key: 'X-Content-Type-Options',
        value: 'nosniff',
      },
      {
        key: 'X-Frame-Options',
        value: 'DENY',
      },
      {
        key: 'Referrer-Policy',
        value: 'strict-origin-when-cross-origin',
      },
      {
        key: 'Permissions-Policy',
        value: 'camera=(), microphone=(), geolocation=()',
      },
    ];

    if (isProd) {
      headersList.push({
        key: 'Strict-Transport-Security',
        value: 'max-age=31536000; includeSubDomains',
      });
    }

    return [
      {
        source: '/(.*)',
        headers: headersList,
      },
    ];
  },
};

export default nextConfig;
