import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api/client";

const tabs = [
  ["/intake", "Intake"],
  ["/profile", "Profile"],
  ["/plan", "Meal plan"],
  ["/grocery", "Groceries"],
  ["/pantry", "Pantry"],
] as const;

export default function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });

  return (
    <main className="container">
      <hgroup>
        <h2 className="brand">
          Meat &amp; Potatoes <small>— weekly meal planning, straight to your Walmart cart</small>
        </h2>
      </hgroup>

      <nav className="topbar">
        <ul>
          {tabs.map(([to, label]) => (
            <li key={to}>
              <NavLink to={to} className={({ isActive }) => (isActive ? "active" : "")}>
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
        <ul>
          <li className="muted">
            {health.data
              ? `provider: ${health.data.provider} · model: ${health.data.model}`
              : health.isError
                ? "backend offline"
                : "…"}
          </li>
        </ul>
      </nav>

      <Outlet />
    </main>
  );
}
