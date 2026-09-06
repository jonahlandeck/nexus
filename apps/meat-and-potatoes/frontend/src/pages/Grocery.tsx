import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type CartLink, type GroceryList, type Plan } from "../api/client";
import ProductRow from "../components/ProductRow";

export default function Grocery() {
  const qc = useQueryClient();
  const [cart, setCart] = useState<CartLink | null>(null);
  const [chunk, setChunk] = useState(1);
  const [stepIdx, setStepIdx] = useState(0);
  const [added, setAdded] = useState<Set<number>>(() => new Set());

  const resetCart = () => {
    setCart(null);
    setStepIdx(0);
    setAdded(new Set());
  };

  const plan = useQuery<Plan>({ queryKey: ["plan", "latest"], queryFn: api.latestPlan, retry: false });
  const planId = plan.data?.id;

  const list = useQuery<GroceryList>({
    queryKey: ["grocery", planId],
    queryFn: () => api.groceryList(planId!),
    enabled: !!planId,
  });

  const stats = useQuery({
    queryKey: ["grocery", "cache"],
    queryFn: api.cacheStats,
    enabled: !!planId,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["grocery"] });
    resetCart();
  };

  const matchAll = useMutation({
    mutationFn: (force: boolean) => api.match(planId!, force),
    onSuccess: (data) => {
      qc.setQueryData(["grocery", planId], data);
      qc.invalidateQueries({ queryKey: ["grocery", "cache"] });
      resetCart();
    },
  });

  const override = useMutation({
    mutationFn: (v: { id: number; body: Parameters<typeof api.overrideMatch>[1] }) =>
      api.overrideMatch(v.id, v.body),
    onSuccess: invalidate,
  });

  const buildCart = useMutation({
    mutationFn: () => api.cartLink(planId!, chunk),
    onSuccess: (data) => {
      setCart(data);
      setStepIdx(0);
      setAdded(new Set());
    },
  });

  const openStep = (i: number) => {
    const s = cart?.steps[i];
    if (!s) return;
    window.open(s.url, "_blank", "noopener,noreferrer");
    setAdded((prev) => new Set(prev).add(s.index));
    setStepIdx(i + 1);
  };

  if (plan.isError || !planId)
    return (
      <p className="muted">
        No meal plan yet. Generate one on the <Link to="/plan">Meal plan</Link> tab first.
      </p>
    );

  const g = list.data;
  const matchByKey = new Map((g?.matches ?? []).map((m) => [m.line_key, m]));
  const busy = matchAll.isPending || override.isPending;
  const noPrices =
    !!g && g.matches.length > 0 && g.matches.every((m) => m.price == null) && g.provider !== "mock";

  return (
    <section>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={() => matchAll.mutate(false)} aria-busy={matchAll.isPending}>
          Find Walmart products
        </button>
        <button className="secondary" onClick={() => matchAll.mutate(true)} disabled={busy}>
          Re-check prices (force refresh)
        </button>
        {g && (
          <span className="muted">
            provider: {g.provider}
            {stats.data
              ? ` · cache: ${stats.data.entries} saved, ${stats.data.hits} hits / ${stats.data.misses} misses`
              : ""}
          </span>
        )}
      </div>

      {matchAll.isError && <p className="err">{(matchAll.error as Error).message}</p>}
      {list.isLoading && <p aria-busy="true">Loading list…</p>}
      {noPrices && (
        <p className="muted">
          Walmart's search feed didn't include prices for these items — the cart link still works,
          you'll see prices on Walmart when you open it.
        </p>
      )}

      {g && (
        <>
          <table className="grocery">
            <thead>
              <tr>
                <th>Ingredient</th>
                <th></th>
                <th>Walmart product</th>
                <th>Price</th>
                <th>Stock</th>
                <th>Qty</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              {g.lines.map((line) => (
                <ProductRow
                  key={line.line_key}
                  line={line}
                  match={matchByKey.get(line.line_key)}
                  busy={busy}
                  onRequery={(id, query) => override.mutate({ id, body: { query } })}
                  onSetItemId={(id, item_id) => override.mutate({ id, body: { item_id } })}
                  onQty={(id, cart_quantity) => override.mutate({ id, body: { cart_quantity } })}
                />
              ))}
            </tbody>
          </table>

          <div
            style={{
              display: "flex",
              gap: "1rem",
              alignItems: "baseline",
              marginTop: "1rem",
              flexWrap: "wrap",
            }}
          >
            <strong>
              Estimated total: {g.estimated_total != null ? `$${g.estimated_total.toFixed(2)}` : "—"}
            </strong>
            <label className="muted">
              items per link:{" "}
              <select
                value={chunk}
                onChange={(e) => {
                  setChunk(Number(e.target.value));
                  resetCart();
                }}
              >
                <option value={1}>1 (one at a time)</option>
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </label>
            <button onClick={() => buildCart.mutate()} aria-busy={buildCart.isPending}>
              Build Walmart cart links →
            </button>
          </div>

          {cart?.warning && <p className="err">{cart.warning}</p>}

          {cart && cart.steps.length > 0 && (
            <article style={{ marginTop: "1rem" }}>
              <p>
                Walmart drops items when one link carries the whole cart, so this is split into{" "}
                <strong>{cart.steps.length}</strong> small links. Open each one while signed in to
                walmart.com — a tab opens, adds{chunk > 1 ? " those items" : " that item"}, and you
                come back here for the next.
              </p>

              <p className="muted">
                {added.size} / {cart.steps.length} opened
              </p>

              {stepIdx < cart.steps.length ? (
                <div
                  style={{
                    display: "flex",
                    gap: "0.75rem",
                    alignItems: "center",
                    flexWrap: "wrap",
                  }}
                >
                  <button onClick={() => openStep(stepIdx)}>
                    Add step {cart.steps[stepIdx].index} of {cart.steps.length} →
                  </button>
                  <span>{cart.steps[stepIdx].label}</span>
                  <button
                    className="secondary"
                    onClick={() => setStepIdx(stepIdx + 1)}
                    disabled={stepIdx >= cart.steps.length}
                  >
                    Skip
                  </button>
                  {stepIdx > 0 && (
                    <button className="secondary" onClick={() => setStepIdx(stepIdx - 1)}>
                      ← Back
                    </button>
                  )}
                </div>
              ) : (
                <p>
                  <strong>All {cart.steps.length} links opened.</strong> Check your Walmart cart —
                  re-open any step below if one didn't take.
                </p>
              )}

              <details style={{ marginTop: "1rem" }}>
                <summary className="muted">All links</summary>
                <ol>
                  {cart.steps.map((s) => (
                    <li key={s.index}>
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={() => setAdded((prev) => new Set(prev).add(s.index))}
                      >
                        {s.label}
                      </a>
                      {added.has(s.index) && <span className="muted"> ✓</span>}
                    </li>
                  ))}
                </ol>
                <p className="muted" style={{ marginTop: "0.5rem" }}>
                  All-in-one link (often drops items on large carts):
                </p>
                <input readOnly value={cart.url} onFocus={(e) => e.currentTarget.select()} />
              </details>

              {cart.missing.length > 0 && (
                <p className="pill miss">
                  No product picked for: {cart.missing.join(", ")} — search or paste an item id above.
                </p>
              )}
            </article>
          )}
        </>
      )}
    </section>
  );
}
