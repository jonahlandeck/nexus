import type { Meal } from "../api/client";

function qty(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

export default function MealCard({ meal }: { meal: Meal }) {
  return (
    <article className="meal-card">
      <div className="slot">{meal.slot}</div>
      <strong>{meal.title}</strong>
      {meal.approx_calories ? <span className="muted"> · ~{meal.approx_calories} kcal</span> : null}
      {meal.description ? <p className="muted">{meal.description}</p> : null}
      <ul>
        {meal.ingredients.map((ing) => (
          <li key={ing.id}>
            {qty(ing.quantity)} {ing.unit} {ing.name}
            {ing.staple ? <span className="muted"> (staple)</span> : null}
          </li>
        ))}
      </ul>
    </article>
  );
}
