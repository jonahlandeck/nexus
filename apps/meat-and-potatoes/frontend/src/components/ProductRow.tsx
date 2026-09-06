import { useState } from "react";
import type { ProductMatch, ShoppingLine } from "../api/client";

interface Props {
  line: ShoppingLine;
  match?: ProductMatch;
  onRequery: (id: number, query: string) => void;
  onSetItemId: (id: number, itemId: string) => void;
  onQty: (id: number, qty: number) => void;
  busy: boolean;
}

function fmtQty(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

export default function ProductRow({ line, match, onRequery, onSetItemId, onQty, busy }: Props) {
  const [q, setQ] = useState(match?.query ?? line.name);
  const [manualId, setManualId] = useState("");

  return (
    <tr>
      <td>
        <strong>{line.name}</strong>
        <br />
        <span className="muted">
          need {fmtQty(line.quantity)} {line.unit} · {line.category || "misc"}
        </span>
      </td>
      <td>
        {match?.image_url ? <img src={match.image_url} alt="" /> : null}
      </td>
      <td>
        {match?.item_id ? (
          <>
            <a href={match.product_url ?? "#"} target="_blank" rel="noreferrer">
              {match.product_name ?? match.item_id}
            </a>
            <br />
            <span className="muted">
              {match.seller ?? "Walmart"} · item {match.item_id}
              {match.manual ? " · manual" : ""}
            </span>
          </>
        ) : match?.search_url ? (
          <a href={match.search_url} target="_blank" rel="noreferrer">
            search Walmart for “{match.query}”
          </a>
        ) : (
          <span className="muted">no match</span>
        )}
      </td>
      <td>{match?.price != null ? `$${match.price.toFixed(2)}` : "—"}</td>
      <td>{match ? (match.in_stock ? <span className="pill">in stock</span> : <span className="oos">out</span>) : "—"}</td>
      <td>
        {match ? (
          <input
            type="number"
            min={1}
            value={match.cart_quantity}
            style={{ width: "4.5rem" }}
            onChange={(e) => onQty(match.id, Math.max(1, Number(e.target.value) || 1))}
          />
        ) : null}
      </td>
      <td>
        {match ? (
          <div className="row-actions">
            <input
              type="search"
              value={q}
              placeholder="re-search"
              onChange={(e) => setQ(e.target.value)}
              style={{ width: "9rem" }}
            />
            <button className="secondary" disabled={busy} onClick={() => onRequery(match.id, q)}>
              search
            </button>
            <input
              type="text"
              value={manualId}
              placeholder="paste item id"
              onChange={(e) => setManualId(e.target.value)}
              style={{ width: "7rem" }}
            />
            <button
              className="secondary"
              disabled={busy || !manualId.trim()}
              onClick={() => {
                onSetItemId(match.id, manualId.trim());
                setManualId("");
              }}
            >
              set
            </button>
          </div>
        ) : null}
      </td>
    </tr>
  );
}
