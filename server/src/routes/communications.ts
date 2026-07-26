import { Router } from "express";
import { z } from "zod";
import { prisma } from "../lib/db.js";

export const communicationsRouter = Router();

// Inbound emails that didn't match any known client's address —
// surfaced so the user can triage and link them to a client.
communicationsRouter.get("/unmatched", async (_req, res) => {
  const items = await prisma.communication.findMany({
    where: { clientId: null },
    orderBy: { occurredAt: "desc" },
    take: 100,
  });
  res.json(items);
});

const assignSchema = z.object({ clientId: z.string().min(1) });

communicationsRouter.post("/:id/assign", async (req, res) => {
  const parsed = assignSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.flatten() });
    return;
  }
  const comm = await prisma.communication.update({
    where: { id: req.params.id },
    data: { clientId: parsed.data.clientId },
  });
  res.json(comm);
});

communicationsRouter.post("/:id/handled", async (req, res) => {
  const comm = await prisma.communication.update({
    where: { id: req.params.id },
    data: { handled: true },
  });
  res.json(comm);
});
