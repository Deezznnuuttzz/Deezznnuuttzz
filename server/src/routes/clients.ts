import { Router } from "express";
import { z } from "zod";
import { prisma } from "../lib/db.js";

export const clientsRouter = Router();

clientsRouter.get("/", async (_req, res) => {
  const clients = await prisma.client.findMany({
    include: {
      emailAddresses: true,
      communications: {
        orderBy: { occurredAt: "desc" },
        take: 1,
      },
    },
    orderBy: { name: "asc" },
  });

  const withStatus = clients.map((c) => {
    const last = c.communications[0];
    return {
      id: c.id,
      name: c.name,
      company: c.company,
      emailAddresses: c.emailAddresses.map((e) => e.email),
      lastCommunicationAt: last?.occurredAt ?? null,
      needsFollowUp: Boolean(last && last.direction === "INBOUND" && !last.handled),
    };
  });

  res.json(withStatus);
});

const createClientSchema = z.object({
  name: z.string().min(1),
  company: z.string().optional(),
  notes: z.string().optional(),
  emailAddresses: z.array(z.string().email()).default([]),
});

clientsRouter.post("/", async (req, res) => {
  const parsed = createClientSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.flatten() });
    return;
  }

  const { emailAddresses, ...data } = parsed.data;
  try {
    const client = await prisma.client.create({
      data: {
        ...data,
        emailAddresses: {
          create: emailAddresses.map((email) => ({ email: email.toLowerCase() })),
        },
      },
      include: { emailAddresses: true },
    });
    res.status(201).json(client);
  } catch (err) {
    res.status(409).json({ error: "One of these email addresses is already linked to a client" });
  }
});

const updateClientSchema = z.object({
  name: z.string().min(1).optional(),
  company: z.string().optional(),
  notes: z.string().optional(),
});

clientsRouter.get("/:id", async (req, res) => {
  const client = await prisma.client.findUnique({
    where: { id: req.params.id },
    include: {
      emailAddresses: true,
      communications: { orderBy: { occurredAt: "desc" } },
    },
  });
  if (!client) {
    res.status(404).json({ error: "Client not found" });
    return;
  }
  res.json(client);
});

clientsRouter.put("/:id", async (req, res) => {
  const parsed = updateClientSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.flatten() });
    return;
  }
  const client = await prisma.client.update({ where: { id: req.params.id }, data: parsed.data });
  res.json(client);
});

clientsRouter.delete("/:id", async (req, res) => {
  await prisma.client.delete({ where: { id: req.params.id } });
  res.status(204).end();
});

const addEmailSchema = z.object({ email: z.string().email() });

clientsRouter.post("/:id/emails", async (req, res) => {
  const parsed = addEmailSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.flatten() });
    return;
  }
  try {
    const record = await prisma.clientEmailAddress.create({
      data: { clientId: req.params.id, email: parsed.data.email.toLowerCase() },
    });
    res.status(201).json(record);
  } catch {
    res.status(409).json({ error: "This email address is already linked to a client" });
  }
});

clientsRouter.delete("/:id/emails/:emailId", async (req, res) => {
  await prisma.clientEmailAddress.delete({ where: { id: req.params.emailId } });
  res.status(204).end();
});
