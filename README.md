# Client CRM

An in-house CRM that scans your email inbox over IMAP, matches messages to
clients, and gives you a dashboard of who you owe a reply to. Text-message
scanning isn't wired up yet — see [SMS](#sms-not-yet-connected) below for why
and how to add it later.

## How it works

- `server/` — Node/Express/TypeScript API + Postgres (via Prisma). A
  background job polls each connected IMAP account on a schedule, pulls new
  messages, and matches the sender/recipient address against your saved
  clients.
- `web/` — React/Vite dashboard: clients, a communication timeline per
  client, an "unmatched senders" triage queue, and email account management.

Data model, in brief: a `Client` has one or more email addresses
(`ClientEmailAddress`). Every synced message becomes a `Communication`,
linked to a client when its address matches, otherwise left unmatched for
you to assign. A `ClientPhoneNumber` table already exists for when SMS is
connected later — no migration will be needed to add it.

## Setup

### 1. Database

```bash
docker compose up -d
```

This starts Postgres on `localhost:5432` with user/password/db `crm`/`crm`/`crm`.
Use your own instance instead if you'd rather not run Docker — just point
`DATABASE_URL` at it.

### 2. Server

```bash
cd server
cp .env.example .env
npm install
```

Fill in `server/.env`:

- `DATABASE_URL` — leave as-is if you used the Docker Compose Postgres.
- `JWT_SECRET`, `ENCRYPTION_KEY` — random 32+ char strings. Generate with
  `openssl rand -hex 32`. `ENCRYPTION_KEY` encrypts IMAP passwords at rest
  (AES-256-GCM) — don't lose it, or reuse it across environments carelessly.
- `APP_PASSWORD_HASH` — a bcrypt hash of the password you'll use to log in.
  Generate it with:
  ```bash
  npm run hash-password -- "your-chosen-password"
  ```
  Paste the output (starts with `$2a$` or `$2b$`) into `.env`.

Then:

```bash
npx prisma migrate dev --name init
npm run dev
```

The API runs on `http://localhost:4000`.

### 3. Web app

```bash
cd web
cp .env.example .env   # points VITE_API_URL at the server
npm install
npm run dev
```

Open `http://localhost:5173`, log in with the password you hashed above.

### 4. Connect an email account

In the app, go to **Email Accounts → Add account**, pick a provider preset
(or "Other" for a custom IMAP host), and enter an **app-specific password**
— not your normal account password. How to get one:

- **Gmail**: requires 2-Step Verification enabled first, then
  [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
  → generate one for "Mail".
- **Outlook / Microsoft 365**: account security settings →
  "App passwords" (only shown if your tenant allows legacy IMAP auth — some
  Microsoft 365 orgs disable it entirely, in which case IMAP won't work and
  you'd need Microsoft Graph API integration instead, which this app doesn't
  implement).
- **iCloud**: [appleid.apple.com](https://appleid.apple.com) → Sign-In and
  Security → App-Specific Passwords.

Once added, the account syncs automatically every 10 minutes (configurable
via `SYNC_CRON_SCHEDULE` in `server/.env`, cron syntax), or click **Sync
now** to trigger it immediately. The first sync looks back
`EMAIL_INITIAL_SYNC_DAYS` (default 30) days; later syncs only fetch new
messages.

If your provider advertises a `\Sent` special-use folder (most do), the
sync also reads it so client detail pages show your outbound replies, not
just what came in.

### 5. Add clients

**Clients → Add client**, with their email address(es). Any inbox message
from/to that address becomes part of their timeline automatically. Messages
from addresses you haven't added yet land in **Unmatched**, where you can
assign them to a client (existing or new) — after that, future messages
from that address match automatically.

The **Dashboard** shows inbound messages that haven't been marked
"handled" — that's your follow-up queue.

## Deployment

Both `server` and `web` are ordinary Node/Vite projects — build with
`npm run build` in each and run behind your usual reverse proxy / hosting
setup. Things to change for production:

- Set `NODE_ENV=production` (makes the session cookie `Secure`, so serve
  the API over HTTPS).
- Point `WEB_ORIGIN` (server) and `VITE_API_URL` (web) at your real
  domains.
- Use a managed/persistent Postgres instance, not the local Docker Compose
  one, and run `npx prisma migrate deploy` against it.
- Keep `JWT_SECRET` and `ENCRYPTION_KEY` out of source control — they're
  already gitignored via `.env`.

## SMS (not yet connected)

There's no generic API for reading a personal phone's text messages, so
this wasn't built into the first version. Two realistic paths if you want
to add it later, both requiring new code in `server/src/routes` plus a
webhook endpoint:

1. **iOS Shortcuts automation** — a Personal Automation ("When I get a
   message") that POSTs the text to a webhook this server would expose.
   Works without a Mac, but each run shows an iOS confirmation notification
   unless you turn that off in Settings.
2. **Mac Messages sync agent** — if iMessage/SMS is synced to a Mac, a small
   script reading the local `chat.db` and pushing new rows to the same kind
   of webhook. Fully silent, but needs a Mac running continuously.

The `ClientPhoneNumber` model and the `Communication.channel` field
(`EMAIL` | `SMS`) already exist for this — adding SMS later is a new
ingestion route, not a schema change.

## Security notes

- This app has no built-in rate limiting on the login endpoint. If you
  deploy it publicly, put it behind a reverse proxy that rate-limits
  `/api/auth/login`, or restrict access at the network level (VPN,
  allowlist).
- IMAP passwords are encrypted at rest but decrypted in memory during sync
  — standard for an app that needs to actively use the credential, but
  worth knowing.
