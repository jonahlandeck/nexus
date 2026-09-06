import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Meal, type Plan } from "../api/client";
import DayColumn from "../components/DayColumn";

const ALL_SLOTS = ["breakfast", "lunch", "dinner", "snack"] as const;

function groupByDay(meals: Meal[]): [string, Meal[]][] {
  const map = new Map<string, Meal[]>();
  for (const m of [...meals].sort((a, b) => a.day_index - b.day_index || a.id - b.id)) {
    if (!map.has(m.day)) map.set(m.day, []);
    map.get(m.day)!.push(m);
  }
  return [...map.entries()];
}

export default function PlanPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [days, setDays] = useState(7);
  const [slots, setSlots] = useState<string[]>(["breakfast", "lunch", "dinner"]);

  const latest = useQuery<Plan>({
    queryKey: ["plan", "latest"],
    queryFn: api.latestPlan,
    retry: false,
  });

  const gen = useMutation({
    mutationFn: () => api.generatePlan(prompt, days, slots),
    onSuccess: (plan) => {
      qc.setQueryData(["plan", "latest"], plan);
      qc.invalidateQueries({ queryKey: ["grocery"] });
    },
  });

  const plan = gen.data ?? latest.data;

  return (
    <section>
      <article>
        <label>
          What are you in the mood for this week? (optional)
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. high-protein, mostly Mediterranean, quick lunches, batch-cook dinners"
          />
        </label>
        <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <label>
            Days
            <input
              type="number"
              min={1}
              max={14}
              value={days}
              onChange={(e) => setDays(Math.min(14, Math.max(1, Number(e.target.value) || 7)))}
              style={{ width: "5rem" }}
            />
          </label>
          <fieldset>
            <legend>Meals per day</legend>
            {ALL_SLOTS.map((s) => (
              <label key={s} style={{ display: "inline-flex", gap: "0.3rem", marginRight: "0.8rem" }}>
                <input
                  type="checkbox"
                  checked={slots.includes(s)}
                  onChange={(e) =>
                    setSlots((cur) =>
                      e.target.checked ? [...cur, s] : cur.filter((x) => x !== s),
                    )
                  }
                />
                {s}
              </label>
            ))}
          </fieldset>
        </div>
        <button onClick={() => gen.mutate()} aria-busy={gen.isPending} disabled={slots.length === 0}>
          {plan ? "Regenerate plan" : "Generate plan"}
        </button>
        {gen.isPending && <p className="muted">Asking the local model… this can take a minute.</p>}
        {gen.isError && <p className="err">{(gen.error as Error).message}</p>}
      </article>

      {!plan && !gen.isPending && (
        <p className="muted">
          No plan yet. Fill out the <Link to="/intake">intake</Link> first, then generate one here.
        </p>
      )}

      {plan && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <h3>Your week {plan.prompt ? <span className="muted">— “{plan.prompt}”</span> : null}</h3>
            <button className="secondary" onClick={() => navigate("/grocery")}>
              Build grocery list →
            </button>
          </div>
          {plan.notes && <p className="muted">{plan.notes}</p>}
          <div className="week-grid">
            {groupByDay(plan.meals).map(([day, meals]) => (
              <DayColumn key={day} day={day} meals={meals} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
