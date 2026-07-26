import { useEffect, useState } from "react";
import { api, type Client, type Communication } from "../lib/api";
import { timeAgo } from "../lib/format";

export function Unmatched() {
  const [items, setItems] = useState<Communication[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [assigning, setAssigning] = useState<Record<string, string>>({});

  function load() {
    api.get<Communication[]>("/communications/unmatched").then(setItems);
    api.get<Client[]>("/clients").then(setClients);
  }

  useEffect(load, []);

  async function assign(commId: string) {
    const clientId = assigning[commId];
    if (!clientId) return;
    await api.post(`/communications/${commId}/assign`, { clientId });
    load();
  }

  return (
    <div>
      <h1>Unmatched senders</h1>
      <p className="muted">
        Emails from addresses that aren't linked to any client yet. Assign them so future emails
        from the same address are matched automatically.
      </p>

      {items.length === 0 && <p className="muted">Nothing to review.</p>}

      <ul className="comm-list">
        {items.map((c) => (
          <li key={c.id} className="comm-item">
            <div>
              <span className="comm-client">{c.fromAddress}</span>
              <span className="comm-subject"> — {c.subject || "(no subject)"}</span>
              <p className="muted comm-snippet">{c.snippet}</p>
              <span className="muted">{timeAgo(c.occurredAt)}</span>
            </div>
            <div className="comm-meta">
              <select
                value={assigning[c.id] ?? ""}
                onChange={(e) => setAssigning((s) => ({ ...s, [c.id]: e.target.value }))}
              >
                <option value="">Assign to client...</option>
                {clients.map((cl) => (
                  <option key={cl.id} value={cl.id}>
                    {cl.name}
                  </option>
                ))}
              </select>
              <button onClick={() => assign(c.id)} disabled={!assigning[c.id]}>
                Assign
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
