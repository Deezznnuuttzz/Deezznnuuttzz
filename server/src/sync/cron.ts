import cron from "node-cron";
import { prisma } from "../lib/db.js";
import { syncEmailAccount } from "./imapSync.js";

const SCHEDULE = process.env.SYNC_CRON_SCHEDULE ?? "*/10 * * * *";

export function startSyncScheduler(): void {
  cron.schedule(SCHEDULE, async () => {
    const accounts = await prisma.emailAccount.findMany({ where: { active: true } });
    for (const account of accounts) {
      try {
        await syncEmailAccount(account.id);
      } catch (err) {
        console.error(`[sync] account ${account.label} failed:`, err instanceof Error ? err.message : err);
      }
    }
  });
  console.log(`[sync] scheduler started with cron "${SCHEDULE}"`);
}
