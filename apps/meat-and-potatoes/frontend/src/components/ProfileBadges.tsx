import type { ProfileData } from "../api/client";

function render(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${k}: ${render(v)}`)
      .join(" · ");
  }
  return String(value);
}

export default function ProfileBadges({ profile }: { profile: ProfileData }) {
  const entries = Object.entries(profile).filter(
    ([, v]) => v !== null && v !== "" && !(Array.isArray(v) && v.length === 0),
  );
  if (entries.length === 0) return <p className="muted">Nothing captured yet — start chatting below.</p>;
  return (
    <div className="badges">
      {entries.map(([k, v]) => (
        <span className="badge" key={k}>
          <b>{k.replace(/_/g, " ")}</b> {render(v)}
        </span>
      ))}
    </div>
  );
}
