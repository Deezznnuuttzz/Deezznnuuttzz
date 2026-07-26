-- CreateEnum
CREATE TYPE "ChannelType" AS ENUM ('EMAIL', 'SMS');

-- CreateEnum
CREATE TYPE "Direction" AS ENUM ('INBOUND', 'OUTBOUND');

-- CreateTable
CREATE TABLE "Client" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "company" TEXT,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Client_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ClientEmailAddress" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "clientId" TEXT NOT NULL,

    CONSTRAINT "ClientEmailAddress_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ClientPhoneNumber" (
    "id" TEXT NOT NULL,
    "phone" TEXT NOT NULL,
    "clientId" TEXT NOT NULL,

    CONSTRAINT "ClientPhoneNumber_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "EmailAccount" (
    "id" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "host" TEXT NOT NULL,
    "port" INTEGER NOT NULL,
    "secure" BOOLEAN NOT NULL DEFAULT true,
    "username" TEXT NOT NULL,
    "encryptedPassword" TEXT NOT NULL,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "lastSyncedAt" TIMESTAMP(3),
    "lastSyncError" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "EmailAccount_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "FolderSyncState" (
    "id" TEXT NOT NULL,
    "emailAccountId" TEXT NOT NULL,
    "folderPath" TEXT NOT NULL,
    "uidValidity" BIGINT NOT NULL,
    "lastSeenUid" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "FolderSyncState_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Communication" (
    "id" TEXT NOT NULL,
    "channel" "ChannelType" NOT NULL DEFAULT 'EMAIL',
    "direction" "Direction" NOT NULL,
    "emailAccountId" TEXT,
    "clientId" TEXT,
    "fromAddress" TEXT NOT NULL,
    "toAddresses" TEXT NOT NULL,
    "subject" TEXT,
    "snippet" TEXT,
    "bodyText" TEXT,
    "externalId" TEXT NOT NULL,
    "occurredAt" TIMESTAMP(3) NOT NULL,
    "handled" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Communication_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ClientEmailAddress_email_key" ON "ClientEmailAddress"("email");

-- CreateIndex
CREATE UNIQUE INDEX "ClientPhoneNumber_phone_key" ON "ClientPhoneNumber"("phone");

-- CreateIndex
CREATE UNIQUE INDEX "FolderSyncState_emailAccountId_folderPath_key" ON "FolderSyncState"("emailAccountId", "folderPath");

-- CreateIndex
CREATE INDEX "Communication_clientId_idx" ON "Communication"("clientId");

-- CreateIndex
CREATE INDEX "Communication_occurredAt_idx" ON "Communication"("occurredAt");

-- CreateIndex
CREATE UNIQUE INDEX "Communication_emailAccountId_externalId_key" ON "Communication"("emailAccountId", "externalId");

-- AddForeignKey
ALTER TABLE "ClientEmailAddress" ADD CONSTRAINT "ClientEmailAddress_clientId_fkey" FOREIGN KEY ("clientId") REFERENCES "Client"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClientPhoneNumber" ADD CONSTRAINT "ClientPhoneNumber_clientId_fkey" FOREIGN KEY ("clientId") REFERENCES "Client"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "FolderSyncState" ADD CONSTRAINT "FolderSyncState_emailAccountId_fkey" FOREIGN KEY ("emailAccountId") REFERENCES "EmailAccount"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Communication" ADD CONSTRAINT "Communication_emailAccountId_fkey" FOREIGN KEY ("emailAccountId") REFERENCES "EmailAccount"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Communication" ADD CONSTRAINT "Communication_clientId_fkey" FOREIGN KEY ("clientId") REFERENCES "Client"("id") ON DELETE SET NULL ON UPDATE CASCADE;
