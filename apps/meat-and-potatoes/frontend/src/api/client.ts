// Typed fetch helpers for the Meat And Potatoes backend.
//
// Every request is prefixed with the app's deploy base so the same build works
// both at the dev-server root (`/api/...`) and mounted under a sub-path in
// production (`/apps/meat-and-potatoes/api/...`). Vite fills in BASE_URL from the
// `--base` flag at build time; it is "/" during local dev.
const API_BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

export interface ProfileData {
  [k: string]: unknown;
}

export interface IntakeResponse {
  session_id: string;
  assistant_message: string;
  profile: ProfileData;
  missing_fields: string[];
  complete: boolean;
}

export interface Ingredient {
  id: number;
  name: string;
  quantity: number;
  unit: string;
  category: string;
  staple: boolean;
}

export interface Meal {
  id: number;
  day: string;
  day_index: number;
  slot: string;
  title: string;
  description: string;
  servings: number;
  approx_calories: number | null;
  ingredients: Ingredient[];
}

export interface Plan {
  id: number;
  prompt: string;
  notes: string;
  days: number;
  created_at: string;
  meals: Meal[];
}

export interface ShoppingLine {
  line_key: string;
  name: string;
  quantity: number;
  unit: string;
  category: string;
}

export interface ProductMatch {
  id: number;
  line_key: string;
  query: string;
  display_name: string;
  quantity_needed: number;
  item_id: string | null;
  product_name: string | null;
  price: number | null;
  in_stock: boolean;
  image_url: string | null;
  product_url: string | null;
  seller: string | null;
  cart_quantity: number;
  manual: boolean;
  search_url: string | null;
}

export interface GroceryList {
  plan_id: number;
  provider: string;
  lines: ShoppingLine[];
  matches: ProductMatch[];
  estimated_total: number | null;
}

export interface CartStep {
  index: number;
  total: number;
  label: string;
  url: string;
  item_ids: string[];
  quantity: number;
}

export interface CartLink {
  url: string;
  item_count: number;
  missing: string[];
  steps: CartStep[];
  warning: string | null;
}

export interface CacheStats {
  entries: number;
  hits: number;
  misses: number;
  last_fetch_at: string | null;
}

export interface PantryItem {
  id: number;
  name: string;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ ok: boolean; provider: string; model: string }>("/api/health"),

  getProfile: () => req<{ data: ProfileData }>("/api/profile"),
  putProfile: (data: ProfileData) =>
    req<{ data: ProfileData }>("/api/profile", {
      method: "PUT",
      body: JSON.stringify({ data }),
    }),

  intake: (message: string, session_id: string | null) =>
    req<IntakeResponse>("/api/intake/message", {
      method: "POST",
      body: JSON.stringify({ message, session_id }),
    }),

  generatePlan: (prompt: string, days: number, meals_per_day: string[]) =>
    req<Plan>("/api/plan/generate", {
      method: "POST",
      body: JSON.stringify({ prompt, days, meals_per_day }),
    }),
  latestPlan: () => req<Plan>("/api/plan/latest"),
  getPlan: (id: number) => req<Plan>(`/api/plan/${id}`),

  groceryList: (planId: number) => req<GroceryList>(`/api/grocery/list/${planId}`),
  match: (plan_id: number, force = false) =>
    req<GroceryList>("/api/grocery/match", {
      method: "POST",
      body: JSON.stringify({ plan_id, force }),
    }),
  overrideMatch: (
    id: number,
    body: { item_id?: string; query?: string; cart_quantity?: number },
  ) =>
    req<ProductMatch>(`/api/grocery/match/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  cartLink: (plan_id: number, chunk_size = 1) =>
    req<CartLink>("/api/grocery/cart-link", {
      method: "POST",
      body: JSON.stringify({ plan_id, chunk_size }),
    }),
  cacheStats: () => req<CacheStats>("/api/grocery/cache/stats"),

  pantry: () => req<PantryItem[]>("/api/pantry"),
  addPantry: (name: string) =>
    req<PantryItem>("/api/pantry", { method: "POST", body: JSON.stringify({ name }) }),
  delPantry: (id: number) => req<{ ok: boolean }>(`/api/pantry/${id}`, { method: "DELETE" }),
};
