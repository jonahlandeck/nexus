/**
 * nexus apex Worker for landeck.pro
 *
 * Owns the `landeck.pro/apps/*` route and serves each registered app as a
 * static single-page app out of ./public/apps/<slug>/. For the Meat & Potatoes
 * app it also stubs the backend: every `/apps/meat-and-potatoes/api/*` request
 * is answered from src/demo-data.ts, so the real FastAPI + Ollama + SQLite
 * stack is not needed to show the UI.
 *
 * Add an app:
 *   1. build its SPA into ./public/apps/<slug>/ (see scripts/build-apps.sh)
 *   2. add a line to APPS below
 *   3. wire an API stub in handleApi() if it needs one
 */

import {
  DEMO_CACHE_STATS,
  DEMO_CART_LINK,
  DEMO_GROCERY,
  DEMO_HEALTH,
  DEMO_MATCHES,
  DEMO_PANTRY,
  DEMO_PLAN,
  DEMO_PROFILE,
  INTAKE_STEPS,
} from "./demo-data";

interface Env {
  ASSETS: Fetcher;
}

const APPS: Record<string, { title: string; api: boolean }> = {
  "meat-and-potatoes": { title: "Meat & Potatoes", api: true },
};

const json = (data: unknown, status = 200): Response =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });

async function readJson(request: Request): Promise<Record<string, unknown>> {
  try {
    const body = await request.json();
    return body && typeof body === "object" ? (body as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === "/" || path === "/apps" || path === "/apps/") {
      return appsIndex(url.origin);
    }

    const parts = path.match(/^\/apps\/([^/]+)(\/.*)?$/);
    if (!parts) return new Response("Not found", { status: 404 });

    const slug = parts[1];
    const rest = parts[2] ?? ""; // "", "/", "/plan", "/api/health", "/assets/x.js"
    const app = APPS[slug];
    if (!app) return appNotFound(url.origin, slug);

    const mount = `/apps/${slug}`;

    // Bare "/apps/<slug>" -> trailing slash, so the SPA's relative asset URLs resolve.
    if (rest === "") return Response.redirect(url.origin + mount + "/", 302);

    // Stubbed backend.
    if (rest === "/api" || rest.startsWith("/api/")) {
      if (!app.api) return json({ detail: "this app has no demo API" }, 404);
      return handleApi(request, rest.replace(/^\/api/, "") || "/");
    }

    // Static asset straight from ./public.
    const asset = await env.ASSETS.fetch(new Request(url.origin + path, request));
    if (asset.status !== 404) return decorate(asset, path);

    // A missing file with an extension (e.g. a stale hashed asset) is a real 404,
    // not a client route — don't hand it the SPA shell.
    if (/\.[a-z0-9]+$/i.test(rest)) return appNotFound(url.origin, slug);

    // SPA fallback: any other path under the mount is a client route. Fetch the
    // mount directory so Workers Assets returns index.html (a direct
    // ".../index.html" fetch 307-redirects to the pretty URL).
    const index = await env.ASSETS.fetch(new Request(url.origin + mount + "/", request));
    if (index.status === 200) {
      return new Response(index.body, {
        status: 200,
        headers: {
          "content-type": "text/html; charset=utf-8",
          "cache-control": "no-store",
        },
      });
    }
    return appNotFound(url.origin, slug);
  },
};

/** Long-cache the content-hashed Vite assets; leave everything else alone. */
function decorate(res: Response, path: string): Response {
  // Vite emits content-hashed files as assets/<name>-<hash>.<ext>
  if (!/\/assets\/[^/]+-[A-Za-z0-9_-]{8,}\.[a-z0-9]+$/.test(path)) return res;
  const headers = new Headers(res.headers);
  headers.set("cache-control", "public, max-age=31536000, immutable");
  return new Response(res.body, { status: res.status, headers });
}

// ---- Meat & Potatoes demo API ------------------------------------------------

function intakeTurn(sessionId: unknown, _message: string) {
  const prev = typeof sessionId === "string" ? sessionId.match(/(\d+)$/) : null;
  const turn = (prev ? Number(prev[1]) : 0) + 1;
  const step = INTAKE_STEPS[Math.min(turn, INTAKE_STEPS.length) - 1];
  return { session_id: `demo-${turn}`, ...step };
}

async function handleApi(request: Request, p: string): Promise<Response> {
  const method = request.method.toUpperCase();

  if (p === "/health") return json(DEMO_HEALTH);

  if (p === "/profile") {
    if (method === "PUT") {
      const body = await readJson(request);
      return json({ data: (body.data as unknown) ?? DEMO_PROFILE });
    }
    return json({ data: DEMO_PROFILE });
  }

  if (p === "/intake/message" && method === "POST") {
    const body = await readJson(request);
    return json(intakeTurn(body.session_id, String(body.message ?? "")));
  }

  if (p === "/plan/generate" && method === "POST") return json(DEMO_PLAN);
  if (p === "/plan/latest") return json(DEMO_PLAN);
  if (/^\/plan\/\d+$/.test(p)) return json(DEMO_PLAN);

  if (/^\/grocery\/list\/\d+$/.test(p)) return json(DEMO_GROCERY);
  if (p === "/grocery/match" && method === "POST") return json(DEMO_GROCERY);
  if (p === "/grocery/cart-link" && method === "POST") return json(DEMO_CART_LINK);
  if (p === "/grocery/cache/stats") return json(DEMO_CACHE_STATS);

  const override = p.match(/^\/grocery\/match\/(\d+)$/);
  if (override && method === "PUT") {
    const id = Number(override[1]);
    const body = await readJson(request);
    const base =
      DEMO_MATCHES.find((m) => m.id === id) ?? DEMO_MATCHES[0];
    return json({
      ...base,
      ...(body.cart_quantity != null
        ? { cart_quantity: Math.max(1, Number(body.cart_quantity)) }
        : {}),
      ...(body.query
        ? { query: String(body.query), display_name: String(body.query), manual: true }
        : {}),
      ...(body.item_id != null
        ? {
            item_id: String(body.item_id).trim() || null,
            manual: true,
            in_stock: true,
          }
        : {}),
    });
  }

  if (p === "/pantry") {
    if (method === "POST") {
      const body = await readJson(request);
      return json({
        id: Math.floor(Math.random() * 1_000_000) + 1000,
        name: String(body.name ?? "").trim(),
      });
    }
    return json(DEMO_PANTRY);
  }
  if (/^\/pantry\/\d+$/.test(p) && method === "DELETE") return json({ ok: true });

  return json({ detail: `demo API has no route for ${method} ${p}` }, 404);
}

// ---- little landing / error pages -----------------------------------------

function page(title: string, body: string, status = 200): Response {
  return new Response(
    `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">` +
      `<title>${title}</title>` +
      `<style>body{font:16px/1.6 system-ui,sans-serif;max-width:34rem;margin:12vh auto;padding:0 1.25rem;color:#222}` +
      `a{color:#b4530a}h1{font-size:1.4rem}code{background:#f0f0f0;padding:.1em .35em;border-radius:4px}</style>` +
      body,
    { status, headers: { "content-type": "text/html; charset=utf-8" } },
  );
}

function appsIndex(origin: string): Response {
  const items = Object.entries(APPS)
    .map(
      ([slug, a]) =>
        `<li><a href="${origin}/apps/${slug}/">${a.title}</a> — <code>/apps/${slug}</code></li>`,
    )
    .join("");
  return page("landeck.pro / apps", `<h1>apps on landeck.pro</h1><ul>${items}</ul>`);
}

function appNotFound(origin: string, slug: string): Response {
  return page(
    "Not found",
    `<h1>No app called “${slug}”</h1><p>See <a href="${origin}/apps">the app list</a>.</p>`,
    404,
  );
}
