import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Client, type Communication } from "../lib/api";
import { timeAgo } from "../lib/format";

type ClientWithDetail = Client & {
  emailAddresses: { id: string; email: string }[];
  communications: Communication[];
  notes: string | null;
};

export function ClientDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [client, setClient] = useState<ClientWithDetail | null>(null);
  const [newEmail, setNewEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!id) return;
    api.get<ClientWithDetail>(`/clients/${id}`).then(setClient);
  }

  useEffect(load, [id]);

  async function addEmail(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post(`/clients/${id}/emails`, { email: newEmail });
      setNewEmail("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add email");
    }
  }

  async function removeEmail(emailId: string) {
    await api.delete(`/clients/${id}/emails/${emailId}`);
    load();
  }

  async function markHandled(commId: string) {
    await api.post(`/communications/${commId}/handled`);
    load();
  }

  async function deleteClient() {
    if (!confirm("Delete this client? Their linked emails will be unassigned, not deleted.")) return;
    await api.delete(`/clients/${id}`);
    navigate("/clients");
  }

  if (!client) return <p className="muted">Loading...</p>;

  return (
    <div>
      <div className="page-header">
        <h1>{client.name}</h1>
        <button className="danger" onClick={deleteClient}>
          Delete client
        </button>
      </div>
      {client.company && <p className="muted">{client.company}</p>}

      <section>
        <h2>Email addresses</h2>
        <ul className="tag-list">
          {client.emailAddresses.map((e) => (
            <li key={e.id} className="tag">
              {e.email}
              <button className="tag-remove" onClick={() => removeEmail(e.id)}>
                ×
              </button>
            </li>
          ))}
        </ul>
        <form className="inline-form" onSubmit={addEmail}>
          <input
            type="email"
            placeholder="Add email address"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            required
          />
          <button type="submit">Add</button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      <section>
        <h2>Communication timeline</h2>
        {client.communications.length === 0 && <p className="muted">No communications yet.</p>}
        <ul className="comm-list">
          {client.communications.map((c) => (
            <li key={c.id} className="comm-item">
              <div>
                <span className={`badge ${c.direction.toLowerCase()}`}>{c.direction}</span>{" "}
                <span className="comm-subject">{c.subject || "(no subject)"}</span>
                <p className="muted comm-snippet">{c.snippet}</p>
              </div>
              <div className="comm-meta">
                <span className="muted">{timeAgo(c.occurredAt)}</span>
                {!c.handled && c.direction === "INBOUND" && (
                  <button onClick={() => markHandled(c.id)}>Mark handled</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
