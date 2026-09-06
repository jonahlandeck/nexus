import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export default function Pantry() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const items = useQuery({ queryKey: ["pantry"], queryFn: api.pantry });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["pantry"] });
    qc.invalidateQueries({ queryKey: ["grocery"] });
  };

  const add = useMutation({ mutationFn: (n: string) => api.addPantry(n), onSuccess: refresh });
  const del = useMutation({ mutationFn: (id: number) => api.delPantry(id), onSuccess: refresh });

  return (
    <section>
      <p>
        Things you already keep stocked. Anything here is left off the grocery list for every plan.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) {
            add.mutate(name.trim());
            setName("");
          }
        }}
      >
        <fieldset role="group">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. olive oil, salt, soy sauce"
          />
          <button type="submit" disabled={add.isPending || !name.trim()}>
            Add
          </button>
        </fieldset>
      </form>

      {items.data && items.data.length === 0 && <p className="muted">Nothing in the pantry yet.</p>}
      <ul>
        {items.data?.map((it) => (
          <li key={it.id}>
            {it.name}{" "}
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                del.mutate(it.id);
              }}
            >
              remove
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
