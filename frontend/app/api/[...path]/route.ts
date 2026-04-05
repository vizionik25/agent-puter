const BACKEND =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:9999";

/**
 * Catch-all backend proxy that forwards every `/api/[...path]` request to the Python backend,
 * streaming the upstream response (status, headers, and body) back to the browser unchanged.
 *
 * @param req - The incoming Next.js request.
 * @param params - Route params containing the path segments after `/api/`.
 * @returns {Promise<Response>} The proxied response from the backend.
 */
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

// Export the proxy handler for every HTTP method the app uses.
export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
