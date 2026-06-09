import express from 'express';
import cookieParser from 'cookie-parser';
import helmet from 'helmet';
import { LRUCache } from 'lru-cache';
import { PrismaClient } from '@prisma/client';
import { fileURLToPath } from 'url';
import path from 'path';
import { createAuthRouter } from './src/routes/auth.js';
import { createRedirectRouter } from './src/routes/redirect.js';
import { createLinksRouter } from './src/routes/links.js';
import { createApiRouter, getOpenApiSpec } from './src/routes/api.js';
import { authGuard, optionalAuth } from './src/middleware/authGuard.js';
import { generalLimiter } from './src/middleware/rateLimiter.js';
import { errorHandler } from './src/middleware/errorHandler.js';
import { createLink } from './src/services/links.js';
import bcryptjs from 'bcryptjs';
import { createHash, randomBytes } from 'crypto';
import dotenv from 'dotenv';
import jwt from 'jsonwebtoken';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const prisma = new PrismaClient();

// LRU Cache for redirects
const cache = new LRUCache({
  max: 1000,
  ttl: 60 * 60 * 1000 // 1 hour
});

// Middleware
app.use(helmet());
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'src/views'));

// Health check
app.get('/health', async (req, res) => {
  try {
    await prisma.$queryRaw`SELECT 1`;
    res.json({ status: 'ok', db: 'ok' });
  } catch (err) {
    res.status(503).json({ status: 'error', db: 'error' });
  }
});

// OpenAPI spec
app.get('/api/v1/openapi.json', (req, res) => {
  res.json(getOpenApiSpec());
});

// Routes
app.use('/auth', createAuthRouter(prisma));
app.use('/', createLinksRouter(prisma));
app.use('/api/v1', createApiRouter(prisma));

// Home page
app.get('/', optionalAuth, async (req, res) => {
  try {
    res.render('home', { user: req.user, BASE_URL: process.env.BASE_URL });
  } catch (err) {
    console.error('Home error:', err);
    res.status(500).render('error', { error: 'Failed to load home' });
  }
});

// Create short URL on home page
app.post('/', optionalAuth, async (req, res) => {
  try {
    const { url } = req.body;

    if (!url) {
      return res.render('home', { user: req.user, error: 'URL is required', BASE_URL: process.env.BASE_URL });
    }

    try {
      new URL(url);
    } catch {
      return res.render('home', { user: req.user, error: 'Invalid URL format', BASE_URL: process.env.BASE_URL });
    }

    const link = await createLink(prisma, {
      destinationUrl: url,
      userId: req.user?.id || null,
      tier: req.user?.tier || 'free'
    });

    res.render('home', {
      user: req.user,
      result: {
        shortCode: link.shortCode,
        shortUrl: `${process.env.BASE_URL}/${link.shortCode}`,
        expiresAt: link.expiresAt
      },
      BASE_URL: process.env.BASE_URL
    });
  } catch (err) {
    if (err.status) {
      return res.render('home', { user: req.user, error: err.message, BASE_URL: process.env.BASE_URL });
    }
    console.error('Create link error:', err);
    res.render('home', { user: req.user, error: 'Failed to create link', BASE_URL: process.env.BASE_URL });
  }
});

// Account page
app.get('/account', authGuard, async (req, res) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.user.id }
    });

    const apiKeys = await prisma.apiKey.findMany({
      where: { userId: req.user.id, revokedAt: null }
    });

    res.render('account', { user, apiKeys });
  } catch (err) {
    console.error('Account error:', err);
    res.status(500).render('error', { error: 'Failed to load account' });
  }
});

// Change password
app.post('/account/change-password', authGuard, async (req, res) => {
  try {
    const { currentPassword, newPassword } = req.body;

    const user = await prisma.user.findUnique({
      where: { id: req.user.id }
    });

    const valid = await bcryptjs.compare(currentPassword, user.passwordHash);
    if (!valid) {
      return res.render('account', { user, error: 'Invalid current password' });
    }

    const hash = await bcryptjs.hash(newPassword, 10);
    await prisma.user.update({
      where: { id: req.user.id },
      data: { passwordHash: hash }
    });

    res.render('account', { user, message: 'Password changed successfully' });
  } catch (err) {
    console.error('Change password error:', err);
    res.status(500).render('error', { error: 'Failed to change password' });
  }
});

// API Key routes
app.post('/account/api-keys/create', authGuard, async (req, res) => {
  try {
    const { label } = req.body;
    const user = await prisma.user.findUnique({ where: { id: req.user.id } });

    const maxKeys = user.tier === 'pro' ? 5 : 1;
    const count = await prisma.apiKey.count({
      where: { userId: req.user.id, revokedAt: null }
    });

    if (count >= maxKeys) {
      return res.render('account', { user, error: 'Maximum API keys reached' });
    }

    const rawKey = randomBytes(32).toString('hex');
    const keyHash = createHash('sha256').update(rawKey).digest('hex');

    await prisma.apiKey.create({
      data: {
        userId: req.user.id,
        keyHash,
        label: label || 'API Key'
      }
    });

    res.render('account', { user, message: `API key created: ${rawKey}. Save it now, you won't see it again!` });
  } catch (err) {
    console.error('Create API key error:', err);
    res.status(500).render('error', { error: 'Failed to create API key' });
  }
});

app.post('/account/api-keys/:keyId/revoke', authGuard, async (req, res) => {
  try {
    const { keyId } = req.params;

    const apiKey = await prisma.apiKey.findUnique({ where: { id: keyId } });
    if (!apiKey || apiKey.userId !== req.user.id) {
      return res.status(404).render('error', { error: 'API key not found' });
    }

    await prisma.apiKey.update({
      where: { id: keyId },
      data: { revokedAt: new Date() }
    });

    const user = await prisma.user.findUnique({ where: { id: req.user.id } });
    res.render('account', { user, message: 'API key revoked' });
  } catch (err) {
    console.error('Revoke API key error:', err);
    res.status(500).render('error', { error: 'Failed to revoke API key' });
  }
});

// Delete account
app.post('/account/delete', authGuard, async (req, res) => {
  try {
    // Soft delete all links
    await prisma.link.updateMany({
      where: { userId: req.user.id },
      data: { deletedAt: new Date() }
    });

    // Soft delete user
    await prisma.user.update({
      where: { id: req.user.id },
      data: { deletedAt: new Date() }
    });

    res.clearCookie('auth_token');
    res.redirect('/');
  } catch (err) {
    console.error('Delete account error:', err);
    res.status(500).render('error', { error: 'Failed to delete account' });
  }
});

// Billing webhook
app.post('/internal/billing/upgrade', async (req, res) => {
  try {
    const secret = req.headers['x-webhook-secret'];
    if (secret !== process.env.BILLING_WEBHOOK_SECRET) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { userId, newTier } = req.body;
    await prisma.user.update({
      where: { id: userId },
      data: { tier: newTier }
    });

    res.json({ success: true });
  } catch (err) {
    console.error('Webhook error:', err);
    res.status(500).json({ error: 'Server error' });
  }
});

// Redirect router (must be last!)
app.use('/', createRedirectRouter(prisma, cache));

// 404 handler
app.use((req, res) => {
  res.status(404).render('404');
});

// Error handler
app.use(errorHandler);

// Run migrations and start server
async function startServer() {
  try {
    console.log('Running database migrations...');
    await prisma.$executeRawUnsafe(`
      CREATE TABLE IF NOT EXISTS "User" (
        "id" TEXT NOT NULL PRIMARY KEY,
        "email" TEXT NOT NULL UNIQUE,
        "passwordHash" TEXT NOT NULL,
        "tier" TEXT NOT NULL DEFAULT 'free',
        "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "deletedAt" DATETIME
      );

      CREATE TABLE IF NOT EXISTS "Link" (
        "id" TEXT NOT NULL PRIMARY KEY,
        "userId" TEXT,
        "shortCode" TEXT NOT NULL UNIQUE,
        "destinationUrl" TEXT NOT NULL,
        "passwordHash" TEXT,
        "expiresAt" DATETIME,
        "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "deletedAt" DATETIME,
        FOREIGN KEY ("userId") REFERENCES "User" ("id")
      );

      CREATE TABLE IF NOT EXISTS "ClickEvent" (
        "id" TEXT NOT NULL PRIMARY KEY,
        "linkId" TEXT NOT NULL,
        "clickedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "ipAddress" TEXT,
        "userAgent" TEXT,
        "referrer" TEXT,
        "deviceType" TEXT NOT NULL DEFAULT 'unknown',
        FOREIGN KEY ("linkId") REFERENCES "Link" ("id")
      );

      CREATE TABLE IF NOT EXISTS "ApiKey" (
        "id" TEXT NOT NULL PRIMARY KEY,
        "userId" TEXT NOT NULL,
        "keyHash" TEXT NOT NULL,
        "label" TEXT NOT NULL,
        "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "lastUsedAt" DATETIME,
        "revokedAt" DATETIME,
        FOREIGN KEY ("userId") REFERENCES "User" ("id")
      );

      CREATE TABLE IF NOT EXISTS "PasswordResetToken" (
        "id" TEXT NOT NULL PRIMARY KEY,
        "userId" TEXT NOT NULL,
        "tokenHash" TEXT NOT NULL,
        "expiresAt" DATETIME NOT NULL,
        "usedAt" DATETIME,
        FOREIGN KEY ("userId") REFERENCES "User" ("id")
      );

      CREATE INDEX IF NOT EXISTS "Link_shortCode_idx" ON "Link"("shortCode");
      CREATE INDEX IF NOT EXISTS "Link_userId_idx" ON "Link"("userId");
      CREATE INDEX IF NOT EXISTS "ClickEvent_linkId_idx" ON "ClickEvent"("linkId");
      CREATE INDEX IF NOT EXISTS "ApiKey_userId_idx" ON "ApiKey"("userId");
    `);

    console.log('Migrations completed');

    const port = process.env.PORT || 3000;
    app.listen(port, () => {
      console.log(`Server running at http://localhost:${port}`);
    });
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
}

startServer();

// Graceful shutdown
process.on('SIGINT', async () => {
  await prisma.$disconnect();
  process.exit(0);
});
