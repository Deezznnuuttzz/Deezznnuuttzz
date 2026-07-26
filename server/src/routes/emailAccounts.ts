import { Router } from "express";
import { z } from "zod";
import { prisma } from "../lib/db.js";
import { encryptSecret } from "../lib/crypto.js";
import { syncEmailAccount } from "../sync/imapSync.js";

export const emailAccountsRouter = Router();

function serialize(account: {
  id: string;
  label: string;
  host: string;
  port: number;
  secure: boolean;
  username: string;
  active: boolean;
  lastSyncedAt: Date | null;
  lastSyncError: string | null;
}) {
  // Explicit allowlist — never echo encryptedPassword back to the client.
  const { id, label, host, port, secure, username, active, lastSyncedAt, lastSyncError } = account;
  return { id, label, host, port, secure, username, active, lastSyncedAt, lastSyncError };
}

emailAccountsRouter.get("/", async (_req, res) => {
  const accounts = await prisma.emailAccount.findMany({ orderBy: { createdAt: "asc" } });
  res.json(accounts.map(serialize));
});

const createSchema = z.object({
  label: z.string().min(1),
  host: z.string().min(1),
  port: z.number().int().positive().default(993),
  secure: z.boolean().default(true),
  username: z.string().min(1),
  password: z.string().min(1),
});

emailAccountsRouter.post("/", async (req, res) => {
  const parsed = createSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.flatten() });
    return;
  }
  const { password, ...data } = parsed.data;
  const account = await prisma.emailAccount.create({
    data: { ...data, encryptedPassword: encryptSecret(password) },
  });
  res.status(201).json(serialize(account));
});

emailAccountsRouter.delete("/:id", async (req, res) => {
  await prisma.emailAccount.delete({ where: { id: req.params.id } });
  res.status(204).end();
});

emailAccountsRouter.post("/:id/sync", async (req, res) => {
  try {
    const result = await syncEmailAccount(req.params.id);
    res.json({ ok: true, fetched: result.fetched });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    res.status(502).json({ ok: false, error: message });
  }
});
