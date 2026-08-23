/**
 * @type {import('next').NextConfig}
 *
 * The browser always talks to the API same-origin (/api/*) — this keeps HTTPS
 * frontends (Vercel) free of mixed-content blocks. A rewrite proxies /api/* to
 * the FastAPI backend. Override with BACKEND_URL at build time.
 */
const backendUrl = process.env.BACKEND_URL || "http://35.200.149.48";

const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;