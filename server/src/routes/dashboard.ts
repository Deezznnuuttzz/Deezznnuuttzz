import { Router } from "express";
import { prisma } from "../lib/db.js";

export const dashboardRouter = Router();

dashboardRouter.get("/", async (_req, res) => {
  const [needsFollowUp, recent, unmatchedCount, accounts] = await Promise.all([
    prisma.communication.findMany({
      where: { direction: "INBOUND", handled: false, clientId: { not: null } },
      orderBy: { occurredAt: "desc" },
      take: 25,
      include: { client: true },
    }),
    prisma.communication.findMany({
      orderBy: { occurredAt: "desc" },
      take: 15,
      include: { client: true },
    }),
    prisma.communication.count({ where: { clientId: null } }),
    prisma.emailAccount.findMany({
      select: { id: true, label: true, lastSyncedAt: true, lastSyncError: true, active: true },
    }),
  ]);

  res.json({ needsFollowUp, recent, unmatchedCount, accounts });
});
