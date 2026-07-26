import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DashboardData } from "../lib/api";
import { timeAgo } from "../lib/format";

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    api
      .get<DashboardData>("/dashboard")
      .then(setData)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function markHandled(id: string) {
    await api.post(`/communications/${id}/handled`);
    load();
  }

  if (loading || !data) return <p className="muted">Loading...</p>;

  return (
    <div>
      <h1>Dashboard</h1>

      {data.accounts.length === 0 && (
        <div className="callout">
          No email accounts connected yet.{" "}
          <Link to="/email-accounts">Add one</Link> to start scanning for client emails.
        </div>
      )}

      {data.accounts.some((a) => a.lastSyncError) && (
        <div className="callout error">
          One or more email accounts failed to sync. Check{" "}
          <Link to="/email-accounts">Email Accounts</Link> for details.
        </div>
      )}

      {data.unmatchedCount > 0 && (
        <div className="callout">
          {data.unmatchedCount} incoming email{data.unmatchedCount === 1 ? "" : "s"} from unknown
          senders. <Link to="/unmatched">Review and assign to clients</Link>.
        </div>
      )}

      <section>
        <h2>Needs follow-up ({data.needsFollowUp.length})</h2>
        {data.needsFollowUp.length === 0 && <p className="muted">Nothing pending. Nice.</p>}
        <ul className="comm-list">
          {data.needsFollowUp.map((c) => (
            <li key={c.id} className="comm-item">
              <div>
                <Link to={`/clients/${c.clientId}`} className="comm-client">
                  {c.client?.name ?? "Unknown"}
                </Link>
                <span className="comm-subject"> — {c.subject || "(no subject)"}</span>
                <p className="muted comm-snippet">{c.snippet}</p>
              </div>
              <div className="comm-meta">
                <span className="muted">{timeAgo(c.occurredAt)}</span>
                <button onClick={() => markHandled(c.id)}>Mark handled</button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Recent activity</h2>
        <ul className="comm-list">
          {data.recent.map((c) => (
            <li key={c.id} className="comm-item">
              <div>
                <span className={`badge ${c.direction.toLowerCase()}`}>{c.direction}</span>{" "}
                {c.client ? (
                  <Link to={`/clients/${c.client.id}`} className="comm-client">
                    {c.client.name}
                  </Link>
                ) : (
                  <span className="muted">{c.fromAddress}</span>
                )}
                <span className="comm-subject"> — {c.subject || "(no subject)"}</span>
              </div>
              <span className="muted">{timeAgo(c.occurredAt)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
