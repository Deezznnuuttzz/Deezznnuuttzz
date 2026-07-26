import "dotenv/config";
import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import { authRouter } from "./routes/auth.js";
import { clientsRouter } from "./routes/clients.js";
import { emailAccountsRouter } from "./routes/emailAccounts.js";
import { communicationsRouter } from "./routes/communications.js";
import { dashboardRouter } from "./routes/dashboard.js";
import { requireAuth } from "./lib/auth.js";
import { startSyncScheduler } from "./sync/cron.js";

const app = express();
const PORT = Number(process.env.PORT ?? 4000);
const WEB_ORIGIN = process.env.WEB_ORIGIN ?? "http://localhost:5173";

app.use(cors({ origin: WEB_ORIGIN, credentials: true }));
app.use(express.json());
app.use(cookieParser());

app.get("/api/health", (_req, res) => res.json({ ok: true }));

app.use("/api/auth", authRouter);
app.use("/api/clients", requireAuth, clientsRouter);
app.use("/api/email-accounts", requireAuth, emailAccountsRouter);
app.use("/api/communications", requireAuth, communicationsRouter);
app.use("/api/dashboard", requireAuth, dashboardRouter);

app.listen(PORT, () => {
  console.log(`CRM server listening on http://localhost:${PORT}`);
  startSyncScheduler();
});
