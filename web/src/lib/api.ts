const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:4000/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.error ? JSON.stringify(body.error) : message;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

// Types shared with the server's API shape.
export type Client = {
  id: string;
  name: string;
  company: string | null;
  notes?: string | null;
  emailAddresses: string[] | { id: string; email: string }[];
  lastCommunicationAt?: string | null;
  needsFollowUp?: boolean;
};

export type Communication = {
  id: string;
  channel: "EMAIL" | "SMS";
  direction: "INBOUND" | "OUTBOUND";
  clientId: string | null;
  client?: { id: string; name: string } | null;
  fromAddress: string;
  toAddresses: string;
  subject: string | null;
  snippet: string | null;
  bodyText: string | null;
  occurredAt: string;
  handled: boolean;
};

export type EmailAccount = {
  id: string;
  label: string;
  host: string;
  port: number;
  secure: boolean;
  username: string;
  active: boolean;
  lastSyncedAt: string | null;
  lastSyncError: string | null;
};

export type DashboardData = {
  needsFollowUp: Communication[];
  recent: Communication[];
  unmatchedCount: number;
  accounts: Pick<EmailAccount, "id" | "label" | "lastSyncedAt" | "lastSyncError" | "active">[];
};
