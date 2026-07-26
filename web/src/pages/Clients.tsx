import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type Client } from "../lib/api";
import { timeAgo } from "../lib/format";

export function Clients() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    api
      .get<Client[]>("/clients")
      .then(setClients)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/clients", {
        name,
        company: company || undefined,
        emailAddresses: email ? [email] : [],
      });
      setName("");
      setCompany("");
      setEmail("");
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create client");
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Clients</h1>
        <button onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "Add client"}</button>
      </div>

      {showForm && (
        <form className="inline-form" onSubmit={handleCreate}>
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <input placeholder="Company (optional)" value={company} onChange={(e) => setCompany(e.target.value)} />
          <input
            placeholder="Email address (optional)"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button type="submit">Save</button>
          {error && <p className="error">{error}</p>}
        </form>
      )}

      {loading ? (
        <p className="muted">Loading...</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Company</th>
              <th>Emails</th>
              <th>Last contact</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/clients/${c.id}`}>{c.name}</Link>
                </td>
                <td>{c.company || "—"}</td>
                <td>{(c.emailAddresses as string[]).join(", ") || "—"}</td>
                <td>{c.lastCommunicationAt ? timeAgo(c.lastCommunicationAt) : "—"}</td>
                <td>{c.needsFollowUp && <span className="badge inbound">needs reply</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
