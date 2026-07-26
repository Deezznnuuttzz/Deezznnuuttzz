import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";

const COOKIE_NAME = "crm_session";

function getJwtSecret(): string {
  const secret = process.env.JWT_SECRET;
  if (!secret || secret.length < 32) {
    throw new Error("JWT_SECRET env var must be set to a random string of at least 32 characters");
  }
  return secret;
}

export function issueSessionCookie(res: Response): void {
  const token = jwt.sign({ sub: "owner" }, getJwtSecret(), { expiresIn: "30d" });
  res.cookie(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 30 * 24 * 60 * 60 * 1000,
  });
}

export function clearSessionCookie(res: Response): void {
  res.clearCookie(COOKIE_NAME);
}

export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  const token = req.cookies?.[COOKIE_NAME];
  if (!token) {
    res.status(401).json({ error: "Not authenticated" });
    return;
  }
  try {
    jwt.verify(token, getJwtSecret());
    next();
  } catch {
    res.status(401).json({ error: "Session expired" });
  }
}
