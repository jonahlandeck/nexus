"""Cloudflare Python Worker entry point for apps/meat-and-potatoes.

Routing for ``landeck.pro/apps/meat-and-potatoes*``:

  * ``/apps/meat-and-potatoes/api/*`` (and ``/docs``, ``/openapi.json``) -> the
    existing FastAPI app, run through the Workers ASGI adapter. ``root_path``
    strips the mount prefix so the app's own route paths are unchanged.
  * everything else -> the built Vite SPA from the ASSETS binding, looked up
    with the mount prefix removed. Unknown non-file paths fall back to the SPA
    shell (configure ``assets.not_found_handling`` = "single-page-application").

The FastAPI app itself is imported, never redefined - it is the
``meat-and-potatoes-backend`` package (``app/``), pulled in as a path
dependency in the repo-root pyproject.toml and vendored into python_modules/.
"""
from __future__ import annotations

from workers import WorkerEntrypoint
from workers.asgi import fetch as asgi_fetch

from app.main import app

MOUNT = "/apps/meat-and-potatoes"
app.root_path = MOUNT

_ASGI_PREFIXES = ("/api", "/docs", "/redoc", "/openapi.json")


def _is_asgi(sub_path: str) -> bool:
    return any(
        sub_path == p or sub_path.startswith(p + "/") for p in _ASGI_PREFIXES
    )


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        from js import URL

        url = URL.new(request.url)
        path = url.pathname
        sub = path[len(MOUNT) :] if path.startswith(MOUNT) else path
        if not sub:
            sub = "/"

        if _is_asgi(sub):
            return await asgi_fetch(app, request, self.env, self.ctx)

        # Static assets live at the store root, without the mount prefix.
        # (The ASSETS binding's fetch takes a single URL/Request argument.)
        return await self.env.ASSETS.fetch(url.origin + sub)
