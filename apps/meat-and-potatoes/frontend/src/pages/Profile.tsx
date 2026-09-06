import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export default function Profile() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["profile"], queryFn: api.getProfile });
  const [text, setText] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    if (data) setText(JSON.stringify(data.data, null, 2));
  }, [data]);

  const save = useMutation({
    mutationFn: (obj: Record<string, unknown>) => api.putProfile(obj),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });

  function onSave() {
    setErr("");
    try {
      const parsed = JSON.parse(text);
      save.mutate(parsed);
    } catch (e) {
      setErr("That's not valid JSON: " + (e as Error).message);
    }
  }

  if (isLoading) return <p aria-busy="true">Loading…</p>;

  return (
    <section>
      <p>
        The intake conversation fills this in. You can also edit it directly — it's the exact object
        the meal planner reads.
      </p>
      <textarea
        rows={20}
        value={text}
        onChange={(e) => setText(e.target.value)}
        style={{ fontFamily: "ui-monospace, monospace", fontSize: "0.85rem" }}
      />
      {err && <p className="err">{err}</p>}
      {save.isError && <p className="err">{(save.error as Error).message}</p>}
      {save.isSuccess && <p className="muted">Saved.</p>}
      <button onClick={onSave} aria-busy={save.isPending}>
        Save profile
      </button>
    </section>
  );
}
