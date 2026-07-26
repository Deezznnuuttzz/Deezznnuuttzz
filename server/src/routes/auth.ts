import { Router } from "express";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { clearSessionCookie, issueSessionCookie, requireAuth } from "../lib/auth.js";

export const authRouter = Router();

authRouter.get("/me", requireAuth, (_req, res) => {
  res.json({ authenticated: true });
});

const loginSchema = z.object({ password: z.string().min(1) });

authRouter.post("/login", async (req, res) => {
  const parsed = loginSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Password is required" });
    return;
  }

  const hash = process.env.APP_PASSWORD_HASH;
  if (!hash) {
    res.status(500).json({ error: "Server is missing APP_PASSWORD_HASH configuration" });
    return;
  }

  const ok = await bcrypt.compare(parsed.data.password, hash);
  if (!ok) {
    res.status(401).json({ error: "Incorrect password" });
    return;
  }

  issueSessionCookie(res);
  res.json({ ok: true });
});

authRouter.post("/logout", (_req, res) => {
  clearSessionCookie(res);
  res.json({ ok: true });
});
