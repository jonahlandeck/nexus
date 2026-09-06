import type { Meal } from "../api/client";
import MealCard from "./MealCard";

export default function DayColumn({ day, meals }: { day: string; meals: Meal[] }) {
  return (
    <div className="day-col">
      <h4>{day}</h4>
      {meals.map((m) => (
        <MealCard key={m.id} meal={m} />
      ))}
    </div>
  );
}
