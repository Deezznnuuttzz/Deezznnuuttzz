import { ImapFlow, type MailboxObject } from "imapflow";
import { simpleParser } from "mailparser";
import { prisma } from "../lib/db.js";
import { decryptSecret } from "../lib/crypto.js";
import type { Direction as DirectionEnum } from "@prisma/client";

const INITIAL_SYNC_DAYS = Number(process.env.EMAIL_INITIAL_SYNC_DAYS ?? 30);
const MAX_BODY_CHARS = 5000;
const MAX_SNIPPET_CHARS = 200;

type FolderJob = {
  path: string;
  direction: DirectionEnum;
};

export async function syncEmailAccount(accountId: string): Promise<{ fetched: number }> {
  const account = await prisma.emailAccount.findUniqueOrThrow({ where: { id: accountId } });
  const password = decryptSecret(account.encryptedPassword);

  const client = new ImapFlow({
    host: account.host,
    port: account.port,
    secure: account.secure,
    auth: { user: account.username, pass: password },
    logger: false,
  });

  let totalFetched = 0;

  try {
    await client.connect();

    const jobs: FolderJob[] = [{ path: "INBOX", direction: "INBOUND" }];
    const sentFolder = await findSpecialUseFolder(client, "\\Sent");
    if (sentFolder) {
      jobs.push({ path: sentFolder, direction: "OUTBOUND" });
    }

    for (const job of jobs) {
      totalFetched += await syncFolder(client, account.id, account.username, job);
    }

    await prisma.emailAccount.update({
      where: { id: account.id },
      data: { lastSyncedAt: new Date(), lastSyncError: null },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    await prisma.emailAccount.update({
      where: { id: account.id },
      data: { lastSyncError: message },
    });
    throw err;
  } finally {
    await client.logout().catch(() => client.close());
  }

  return { fetched: totalFetched };
}

async function findSpecialUseFolder(client: ImapFlow, flag: string): Promise<string | null> {
  try {
    const list = await client.list();
    const match = list.find((box) => box.specialUse === flag);
    return match?.path ?? null;
  } catch {
    return null;
  }
}

async function syncFolder(
  client: ImapFlow,
  emailAccountId: string,
  ownUsername: string,
  job: FolderJob
): Promise<number> {
  const mailbox = (await client.mailboxOpen(job.path, { readOnly: true })) as MailboxObject;
  const uidValidity = mailbox.uidValidity ?? 0n;

  let state = await prisma.folderSyncState.findUnique({
    where: { emailAccountId_folderPath: { emailAccountId, folderPath: job.path } },
  });

  if (!state) {
    state = await prisma.folderSyncState.create({
      data: { emailAccountId, folderPath: job.path, uidValidity, lastSeenUid: 0 },
    });
  } else if (state.uidValidity !== uidValidity) {
    // Mailbox was recreated server-side; UIDs are no longer comparable, start over.
    state = await prisma.folderSyncState.update({
      where: { id: state.id },
      data: { uidValidity, lastSeenUid: 0 },
    });
  }

  let searchResult: number[] | false;
  if (state.lastSeenUid === 0) {
    const since = new Date(Date.now() - INITIAL_SYNC_DAYS * 24 * 60 * 60 * 1000);
    searchResult = await client.search({ since }, { uid: true });
  } else {
    searchResult = await client.search({ uid: `${state.lastSeenUid + 1}:*` }, { uid: true });
  }
  const uidsToFetch: number[] = searchResult || [];

  if (uidsToFetch.length === 0) {
    return 0;
  }

  let maxUid = state.lastSeenUid;
  let fetched = 0;

  for await (const message of client.fetch(uidsToFetch, { envelope: true, uid: true, source: true })) {
    maxUid = Math.max(maxUid, message.uid);
    if (!message.source) continue;

    const parsed = await simpleParser(message.source);
    const fromAddress = (parsed.from?.value?.[0]?.address ?? message.envelope?.from?.[0]?.address ?? "")
      .toLowerCase();
    const toList = Array.isArray(parsed.to) ? parsed.to : parsed.to ? [parsed.to] : [];
    const toAddresses = toList
      .flatMap((t) => t.value.map((v) => v.address ?? ""))
      .filter(Boolean)
      .join(", ");

    const counterpartyAddress =
      job.direction === "INBOUND" ? fromAddress : toList.flatMap((t) => t.value.map((v) => v.address))[0]?.toLowerCase();

    const client_ = counterpartyAddress
      ? await prisma.clientEmailAddress.findUnique({ where: { email: counterpartyAddress } })
      : null;

    const externalId = parsed.messageId ?? `${job.path}-uid${message.uid}`;
    const bodyText = (parsed.text ?? "").slice(0, MAX_BODY_CHARS);
    const snippet = bodyText.replace(/\s+/g, " ").trim().slice(0, MAX_SNIPPET_CHARS);

    await prisma.communication.upsert({
      where: { emailAccountId_externalId: { emailAccountId, externalId } },
      create: {
        channel: "EMAIL",
        direction: job.direction,
        emailAccountId,
        clientId: client_?.clientId,
        fromAddress: fromAddress || ownUsername,
        toAddresses: toAddresses || ownUsername,
        subject: parsed.subject ?? "(no subject)",
        snippet,
        bodyText,
        externalId,
        occurredAt: parsed.date ?? new Date(),
      },
      update: {},
    });

    fetched += 1;
  }

  if (maxUid > state.lastSeenUid) {
    await prisma.folderSyncState.update({
      where: { id: state.id },
      data: { lastSeenUid: maxUid },
    });
  }

  return fetched;
}
