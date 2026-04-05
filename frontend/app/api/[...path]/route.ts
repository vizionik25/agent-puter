/**
 * Catch-all API proxy route.
 *
 * Forwards every /api/* request from the browser to the Python backend,
 * streaming the response back as-is. This replaces the next.config.ts
 * rewrite, which is unreliable for POST requests in Next.js 16.
 */

const BACKEND =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:9999";

async function proxy(req: Request, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const url = new URL(req.url);
  const target = `${BACKEND}/api/${path.join("/")}${url.search}`;

  const headers = new Headers(req.headers);
  // Remove hop-by-hop headers that shouldn't be forwarded
  headers.delete("host");
  headers.delete("connection");

  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body: req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined,
    // @ts-expect-error — Node 18+ fetch supports duplex for streaming bodies
    duplex: "half",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: upstream.headers,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
