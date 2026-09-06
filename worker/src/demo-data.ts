/**
 * Canned data for the Meat & Potatoes public demo.
 *
 * The real app has a FastAPI backend, a local Ollama model and a SQLite
 * database. None of that runs on Cloudflare, so for the landeck.pro/apps demo
 * the Worker answers every `/api/*` call with the fixtures below. The shapes
 * mirror `apps/meat-and-potatoes/backend/app/schemas.py` exactly so the
 * unmodified frontend renders as if a backend were there.
 */

export interface DemoMatch {
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

const walmart = (id: string) => `https://www.walmart.com/ip/${id}`;
const search = (q: string) =>
  `https://www.walmart.com/search?q=${encodeURIComponent(q)}`;

// ---- profile -----------------------------------------------------------------

const FULL_PROFILE = {
  dietary_pattern: "omnivore",
  allergies: ["shellfish"],
  dislikes: ["cilantro", "blue cheese"],
  cuisines: ["Mediterranean", "Mexican", "Japanese"],
  health_goals: ["high protein", "fat loss"],
  target_calories: 2100,
  macros: { protein_g: 165, carbs_g: 190, fat_g: 70 },
  household_size: 2,
  servings_per_meal: 2,
  weekly_budget_usd: 120,
  cook_time_minutes: 30,
  cooking_skill: "comfortable",
  equipment: ["oven", "stovetop", "air fryer", "blender"],
  meals_per_day: ["breakfast", "lunch", "dinner"],
  leftovers_ok: true,
  week_prompt: "high-protein, quick lunches, batch-cook dinners",
};

// ---- scripted intake conversation ------------------------------------------
// One entry per turn; the Worker picks by turn number (see index.ts). The last
// entry is reused for every turn after it, so the plan stays unlockable.

export const INTAKE_STEPS = [
  {
    assistant_message:
      "Great, thanks! A few quick things: any food allergies or hard no-gos? " +
      "And what's the main goal for these meals — fat loss, muscle, just eating better?",
    profile: { dietary_pattern: "omnivore", household_size: 2 },
    missing_fields: [
      "allergies",
      "health_goals",
      "cook_time_minutes",
      "meals_per_day",
      "cuisines",
      "equipment",
    ],
    complete: false,
  },
  {
    assistant_message:
      "Got it — shellfish allergy, high-protein with some fat loss. " +
      "How much time do you want to spend cooking on a weeknight, and which meals should I plan " +
      "(breakfast / lunch / dinner / snacks)?",
    profile: {
      dietary_pattern: "omnivore",
      allergies: ["shellfish"],
      health_goals: ["high protein", "fat loss"],
      household_size: 2,
      cuisines: ["Mediterranean", "Mexican", "Japanese"],
    },
    missing_fields: ["cook_time_minutes", "meals_per_day", "equipment"],
    complete: false,
  },
  {
    assistant_message:
      "Perfect. Here's what I have: omnivore, shellfish allergy, high-protein with a fat-loss lean, " +
      "cooking for 2, about 30 minutes on weeknights, three meals a day, and you're happy to batch-cook. " +
      "That's plenty to build your week — head to the Meal plan tab whenever you're ready.",
    profile: FULL_PROFILE,
    missing_fields: [],
    complete: true,
  },
];

// ---- weekly plan -----------------------------------------------------------

let ingId = 0;
const ing = (
  name: string,
  quantity: number,
  unit: string,
  category: string,
  staple = false,
) => ({ id: ++ingId, name, quantity, unit, category, staple });

let mealId = 0;
const meal = (
  day: string,
  day_index: number,
  slot: string,
  title: string,
  description: string,
  approx_calories: number,
  ingredients: ReturnType<typeof ing>[],
) => ({
  id: ++mealId,
  day,
  day_index,
  slot,
  title,
  description,
  servings: 2,
  approx_calories,
  ingredients,
});

export const DEMO_PLAN = {
  id: 1,
  prompt: "high-protein, quick lunches, batch-cook dinners",
  notes:
    "Batch-cook the brown rice and roast two trays of chicken on Sunday — " +
    "lunches on days 2 and 3 are built from the leftovers.",
  days: 3,
  created_at: "2026-09-05T17:40:00Z",
  meals: [
    meal("Monday", 0, "breakfast", "Greek yogurt protein bowl", "Yogurt, banana, oats and a spoon of peanut butter, topped with almonds.", 430, [
      ing("Greek yogurt", 1.5, "cup", "dairy"),
      ing("banana", 1, "each", "produce"),
      ing("oats", 0.5, "cup", "grains"),
      ing("peanut butter", 1, "tbsp", "pantry"),
      ing("almonds", 0.25, "cup", "pantry"),
    ]),
    meal("Monday", 0, "lunch", "Chicken & rice power bowl", "Roast chicken over brown rice with steamed broccoli and lemon.", 560, [
      ing("chicken breast", 6, "oz", "meat"),
      ing("brown rice", 1, "cup", "grains"),
      ing("broccoli", 1.5, "cup", "produce"),
      ing("olive oil", 1, "tbsp", "pantry", true),
      ing("lemon", 0.5, "each", "produce"),
    ]),
    meal("Monday", 0, "dinner", "Turkey taco skillet", "One-pan ground turkey with beans, tomatoes and peppers, in warm tortillas.", 620, [
      ing("ground turkey", 8, "oz", "meat"),
      ing("black beans", 1, "can", "canned"),
      ing("canned tomatoes", 1, "can", "canned"),
      ing("bell pepper", 1, "each", "produce"),
      ing("onion", 0.5, "each", "produce"),
      ing("tortilla", 2, "each", "grains"),
    ]),
    meal("Tuesday", 1, "breakfast", "Veggie egg scramble", "Three eggs with spinach and cheddar, toast on the side.", 400, [
      ing("egg", 3, "each", "dairy"),
      ing("spinach", 1, "cup", "produce"),
      ing("cheddar cheese", 1, "oz", "dairy"),
      ing("bread", 2, "each", "grains"),
    ]),
    meal("Tuesday", 1, "lunch", "Mediterranean chickpea salad", "Chickpeas, tomato and spinach with olive oil and lemon — no cook.", 480, [
      ing("chickpeas", 1, "can", "canned"),
      ing("tomato", 1, "cup", "produce"),
      ing("spinach", 2, "cup", "produce"),
      ing("olive oil", 1, "tbsp", "pantry", true),
      ing("lemon", 0.5, "each", "produce"),
    ]),
    meal("Tuesday", 1, "dinner", "Baked salmon with sweet potato", "Oven salmon, roasted sweet potato and broccoli.", 590, [
      ing("salmon", 6, "oz", "seafood"),
      ing("sweet potato", 1, "each", "produce"),
      ing("broccoli", 1.5, "cup", "produce"),
      ing("olive oil", 1, "tbsp", "pantry", true),
    ]),
    meal("Wednesday", 2, "breakfast", "Peanut butter banana oats", "Stovetop oats with milk, banana and peanut butter.", 440, [
      ing("oats", 0.75, "cup", "grains"),
      ing("milk", 1, "cup", "dairy"),
      ing("banana", 1, "each", "produce"),
      ing("peanut butter", 1, "tbsp", "pantry"),
    ]),
    meal("Wednesday", 2, "lunch", "Leftover turkey rice bowl", "Monday's turkey and beans over rice with a little cheddar.", 540, [
      ing("ground turkey", 6, "oz", "meat"),
      ing("brown rice", 1, "cup", "grains"),
      ing("black beans", 0.5, "can", "canned"),
      ing("cheddar cheese", 1, "oz", "dairy"),
    ]),
    meal("Wednesday", 2, "dinner", "Sheet-pan chicken & veggies", "Chicken thighs with potato, carrot and pepper on one tray.", 610, [
      ing("chicken breast", 8, "oz", "meat"),
      ing("potato", 2, "each", "produce"),
      ing("carrot", 1, "cup", "produce"),
      ing("bell pepper", 1, "each", "produce"),
      ing("olive oil", 1, "tbsp", "pantry", true),
    ]),
  ],
};

// ---- grocery list --------------------------------------------------------

interface Row {
  key: string;
  name: string;
  qty: number;
  unit: string;
  category: string;
  product: string;
  price: number;
  id: string;
  cartQty: number;
}

const ROWS: Row[] = [
  { key: "chicken breast|oz", name: "chicken breast", qty: 22, unit: "oz", category: "meat", product: "Fresh Boneless Skinless Chicken Breast (2.5 lb)", price: 9.32, id: "173058800", cartQty: 1 },
  { key: "ground turkey|oz", name: "ground turkey", qty: 14, unit: "oz", category: "meat", product: "Honeysuckle White 93/7 Ground Turkey (1 lb)", price: 5.48, id: "946213774", cartQty: 1 },
  { key: "salmon|oz", name: "salmon", qty: 6, unit: "oz", category: "seafood", product: "Fresh Atlantic Salmon Fillet (1 lb)", price: 11.64, id: "554128390", cartQty: 1 },
  { key: "egg|each", name: "egg", qty: 3, unit: "each", category: "dairy", product: "Great Value Large White Eggs (12 ct)", price: 3.12, id: "145051970", cartQty: 1 },
  { key: "milk|cup", name: "milk", qty: 1, unit: "cup", category: "dairy", product: "Great Value 2% Reduced Fat Milk (1 gal)", price: 3.28, id: "10450115", cartQty: 1 },
  { key: "greek yogurt|cup", name: "Greek yogurt", qty: 1.5, unit: "cup", category: "dairy", product: "Great Value Plain Greek Nonfat Yogurt (32 oz)", price: 4.62, id: "182160184", cartQty: 1 },
  { key: "cheddar cheese|oz", name: "cheddar cheese", qty: 2, unit: "oz", category: "dairy", product: "Great Value Mild Cheddar Shredded Cheese (8 oz)", price: 2.34, id: "10291607", cartQty: 1 },
  { key: "brown rice|cup", name: "brown rice", qty: 3, unit: "cup", category: "grains", product: "Great Value Whole Grain Brown Rice (32 oz)", price: 3.12, id: "563073181", cartQty: 1 },
  { key: "oats|cup", name: "oats", qty: 2, unit: "cup", category: "grains", product: "Great Value Old Fashioned Oats (42 oz)", price: 3.34, id: "37744739", cartQty: 1 },
  { key: "tortilla|each", name: "tortilla", qty: 2, unit: "each", category: "grains", product: "Great Value Flour Tortillas (10 ct)", price: 2.18, id: "26925283", cartQty: 1 },
  { key: "bread|each", name: "bread", qty: 2, unit: "each", category: "grains", product: "Great Value White Sandwich Bread (20 oz)", price: 1.42, id: "10315671", cartQty: 1 },
  { key: "black beans|can", name: "black beans", qty: 1.5, unit: "can", category: "canned", product: "Great Value Black Beans (15 oz can)", price: 0.92, id: "10535325", cartQty: 2 },
  { key: "chickpeas|can", name: "chickpeas", qty: 1, unit: "can", category: "canned", product: "Great Value Garbanzo Beans (15 oz can)", price: 0.92, id: "10535340", cartQty: 1 },
  { key: "canned tomatoes|can", name: "canned tomatoes", qty: 1, unit: "can", category: "canned", product: "Great Value Diced Tomatoes (14.5 oz can)", price: 0.98, id: "16944249", cartQty: 1 },
  { key: "broccoli|cup", name: "broccoli", qty: 4.5, unit: "cup", category: "produce", product: "Fresh Broccoli Crown (1 lb)", price: 1.98, id: "44390979", cartQty: 2 },
  { key: "spinach|cup", name: "spinach", qty: 5, unit: "cup", category: "produce", product: "Fresh Baby Spinach (10 oz)", price: 2.68, id: "23644632", cartQty: 1 },
  { key: "banana|each", name: "banana", qty: 2, unit: "each", category: "produce", product: "Fresh Bananas (1 lb)", price: 0.52, id: "44390948", cartQty: 2 },
  { key: "bell pepper|each", name: "bell pepper", qty: 3, unit: "each", category: "produce", product: "Fresh Green Bell Pepper (each)", price: 0.68, id: "10452503", cartQty: 3 },
  { key: "sweet potato|each", name: "sweet potato", qty: 1, unit: "each", category: "produce", product: "Fresh Sweet Potatoes (1 lb)", price: 1.34, id: "44391015", cartQty: 1 },
  { key: "potato|each", name: "potato", qty: 2, unit: "each", category: "produce", product: "Fresh Russet Potatoes (5 lb)", price: 4.27, id: "10315163", cartQty: 1 },
  { key: "peanut butter|tbsp", name: "peanut butter", qty: 2, unit: "tbsp", category: "pantry", product: "Great Value Creamy Peanut Butter (16 oz)", price: 2.64, id: "10315926", cartQty: 1 },
];

export const DEMO_LINES = ROWS.map((r) => ({
  line_key: r.key,
  name: r.name,
  quantity: r.qty,
  unit: r.unit,
  category: r.category,
}));

export const DEMO_MATCHES: DemoMatch[] = ROWS.map((r, i) => ({
  id: i + 1,
  line_key: r.key,
  query: r.name,
  display_name: r.name,
  quantity_needed: r.qty,
  item_id: r.id,
  product_name: r.product,
  price: r.price,
  in_stock: true,
  image_url: null,
  product_url: walmart(r.id),
  seller: "Walmart",
  cart_quantity: r.cartQty,
  manual: false,
  search_url: search(r.name),
}));

const ESTIMATED_TOTAL = Number(
  ROWS.reduce((sum, r) => sum + r.price * r.cartQty, 0).toFixed(2),
);

export const DEMO_GROCERY = {
  plan_id: 1,
  provider: "demo",
  lines: DEMO_LINES,
  matches: DEMO_MATCHES,
  estimated_total: ESTIMATED_TOTAL,
};

export const DEMO_CART_LINK = {
  url:
    "https://affil.walmart.com/cart/addToCart?items=" +
    ROWS.map((r) => `${r.id}|${r.cartQty}`).join(","),
  item_count: ROWS.length,
  missing: [] as string[],
};

export const DEMO_CACHE_STATS = {
  entries: ROWS.length,
  hits: 11,
  misses: 5,
  last_fetch_at: "2026-09-05T18:12:00Z",
};

export const DEMO_PANTRY = [
  { id: 1, name: "olive oil" },
  { id: 2, name: "salt" },
  { id: 3, name: "black pepper" },
  { id: 4, name: "soy sauce" },
];

export const DEMO_HEALTH = {
  ok: true,
  provider: "demo",
  model: "canned data (no Ollama)",
};

export const DEMO_PROFILE = FULL_PROFILE;
