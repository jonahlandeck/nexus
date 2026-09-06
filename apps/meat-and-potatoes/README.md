# Meat And Potatoes

A locally hosted app that runs a short conversation about your diet and health goals,
generates a weekly meal plan with a **local LLM (Ollama)**, turns it into a consolidated
grocery list, looks each item up on **Walmart via ScraperAPI**, and hands you a single
**"add all to my Walmart cart"** link that uses your own logged-in walmart.com session.

```
apps/meat-and-potatoes/
  backend/    FastAPI            (:8000 local, or the Worker)
  frontend/   React + Vite      (:5173)
```

## Deployment

This app deploys to **Cloudflare Workers** (Python Worker) at
`landeck.pro/apps/meat-and-potatoes`, with persistence on **Cloudflare D1**
instead of SQLite. See [`../../DEPLOY.md`](../../DEPLOY.md). Local dev against the
real Worker runtime + a local D1 is `uv run pywrangler dev` from the repo root.

> The `scripts/dev.sh` / plain-uvicorn flow below predates the Workers move. The
> app now reads its database and config from Worker bindings, so routes that
> touch data need the Worker runtime (`pywrangler dev`); bare `uvicorn
> app.main:app` will not serve them.

## Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| Python 3.11+ | backend | `brew install python@3.12` |
| Node 18+ | frontend | `brew install node` |
| [Ollama](https://ollama.com) | meal-plan generation | `brew install ollama` then `ollama serve` |
| A ScraperAPI key | live Walmart search | https://www.scraperapi.com (free tier available) — optional, only for `MAP_PROVIDER=scraperapi` |

Pull the model:

```sh
ollama pull qwen2.5:7b-instruct
```

(any instruct model works — set `OLLAMA_MODEL` in `.env` to whatever you have).

## Configure

```sh
cp .env.example .env      # .env is gitignored
```

Key settings in `.env`:

- `OLLAMA_MODEL` — the Ollama model to use (`qwen2.5:7b-instruct` by default).
- `MAP_PROVIDER` — how groceries are looked up:
  - `mock` — canned data, no network, no key. Good for clicking through the UI, but its item
    IDs are placeholder hashes, **not real Walmart item numbers** — the add-to-cart link will
    not put anything in a real cart. The Groceries page flags this.
  - `scraperapi` — live Walmart data with real item IDs. Requires `SCRAPERAPI_KEY`. **Use this
    if you want a working cart link.**
  - `links` — no lookups at all; each item just gets a Walmart search link. Zero API credits.
- `SCRAPERAPI_KEY` — paste your key here when you switch to `scraperapi`.
- `SEARCH_CACHE_TTL_DAYS` — how long a cached search result is reused before spending another
  API credit (default 7).

## Run

```sh
./scripts/dev.sh
```

First run creates the Python venv and installs both sides, then starts:

- backend  → http://localhost:8000  (interactive API docs at `/docs`)
- frontend → http://localhost:5173

Open **http://localhost:5173**.

### Flow

1. **Intake** — chat through your diet, restrictions, and goals. When enough is captured the
   "Generate my meal plan" button unlocks. (Everything it learns is visible/editable on the
   **Profile** tab.)
2. **Meal plan** — optionally add a free-text request ("high protein, quick lunches"), pick days
   and meal slots, generate. Re-generate as many times as you like.
3. **Pantry** — list what you already keep stocked; those items are dropped from every list.
4. **Groceries** — "Find Walmart products" matches each consolidated line to a Walmart item
   (price, stock, image). Re-search or paste a specific Walmart item id per line, adjust
   quantities, then **"Build Walmart cart links"** produces a *sequence* of small
   `affil.walmart.com/cart/addToCart?items=…` links (one item per link by default — pick 3/5/10
   per link if you prefer). Walk the stepper, opening each while signed in to walmart.com; every
   item lands in your real cart. A single link carrying the whole cart is kept as a fallback but
   Walmart silently drops items from large batches, which is why the stepper exists.

## Search cache

Every ScraperAPI search is stored in the `search_cache` table keyed by the normalized query.
Repeat searches within `SEARCH_CACHE_TTL_DAYS` are served from SQLite — the backend log prints
`cache=hit` / `cache=miss` so you can see credit usage, and the Groceries page shows a running
`hits / misses` count. "Re-check prices (force refresh)" bypasses the cache for one pass.

## How "add to cart" works

There is no public Walmart API that writes to a shopper's cart. The sanctioned mechanism is the
`affil.walmart.com/cart/addToCart?items=ITEM_ID|QTY,…` deep link: opening it in a browser that is
signed in to walmart.com adds those items to that account's cart. This app just builds those links
from your matched items — no Walmart credentials, no browser automation.

That deep link is not reliable for a whole week's groceries in one shot: past roughly a dozen items
(or a long URL) Walmart adds the first few and drops the rest with no error. So `/api/grocery/cart-link`
returns a `steps[]` array — the cart split into `chunk_size` groups (default 1), each its own
addToCart URL — and the Groceries page walks them one at a time. The all-in-one `url` is still
returned as a fallback.

## Tests

```sh
cd backend && .venv/bin/python -m pytest
```

Covers grocery-list consolidation, pantry subtraction, the search cache (hit / miss / TTL /
force-refresh, asserting repeat queries make only one HTTP call), the cart-link format, and the
intake profile-merge logic. None of the tests need Ollama or a network.
