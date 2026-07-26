import { useEffect, useState, type FormEvent } from "react";
import { api, type EmailAccount } from "../lib/api";
import { timeAgo } from "../lib/format";

const PROVIDER_PRESETS: Record<string, { host: string; port: number }> = {
  Gmail: { host: "imap.gmail.com", port: 993 },
  Outlook: { host: "outlook.office365.com", port: 993 },
  iCloud: { host: "imap.mail.me.com", port: 993 },
  Other: { host: "", port: 993 },
};

export function EmailAccounts() {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [preset, setPreset] = useState("Gmail");
  const [label, setLabel] = useState("");
  const [host, setHost] = useState(PROVIDER_PRESETS.Gmail.host);
  const [port, setPort] = useState(PROVIDER_PRESETS.Gmail.port);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  function load() {
    api.get<EmailAccount[]>("/email-accounts").then(setAccounts);
  }

  useEffect(load, []);

  function applyPreset(name: string) {
    setPreset(name);
    const p = PROVIDER_PRESETS[name];
    setHost(p.host);
    setPort(p.port);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/email-accounts", { label, host, port, secure: true, username, password });
      setShowForm(false);
      setLabel("");
      setUsername("");
      setPassword("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add account");
    }
  }

  async function remove(id: string) {
    if (!confirm("Remove this email account? Synced communications will be kept.")) return;
    await api.delete(`/email-accounts/${id}`);
    load();
  }

  async function syncNow(id: string) {
    setSyncingId(id);
    try {
      await api.post(`/email-accounts/${id}/sync`);
    } finally {
      setSyncingId(null);
      load();
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Email Accounts</h1>
        <button onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "Add account"}</button>
      </div>

      {showForm && (
        <form className="inline-form-block" onSubmit={handleCreate}>
          <label>
            Provider
            <select value={preset} onChange={(e) => applyPreset(e.target.value)}>
              {Object.keys(PROVIDER_PRESETS).map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <input placeholder="Label (e.g. Work Gmail)" value={label} onChange={(e) => setLabel(e.target.value)} required />
          <input placeholder="IMAP host" value={host} onChange={(e) => setHost(e.target.value)} required />
          <input
            placeholder="Port"
            type="number"
            value={port}
            onChange={(e) => setPort(Number(e.target.value))}
            required
          />
          <input
            placeholder="Email / username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            placeholder="App password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <p className="muted">
            Use an app-specific password, not your normal login password — see the README for
            provider-specific instructions.
          </p>
          <button type="submit">Save account</button>
          {error && <p className="error">{error}</p>}
        </form>
      )}

      <table className="table">
        <thead>
          <tr>
            <th>Label</th>
            <th>Host</th>
            <th>Username</th>
            <th>Last synced</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((a) => (
            <tr key={a.id}>
              <td>{a.label}</td>
              <td>{a.host}</td>
              <td>{a.username}</td>
              <td>
                {a.lastSyncedAt ? timeAgo(a.lastSyncedAt) : "never"}
                {a.lastSyncError && <div className="error">{a.lastSyncError}</div>}
              </td>
              <td>
                <button onClick={() => syncNow(a.id)} disabled={syncingId === a.id}>
                  {syncingId === a.id ? "Syncing..." : "Sync now"}
                </button>{" "}
                <button className="danger" onClick={() => remove(a.id)}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
