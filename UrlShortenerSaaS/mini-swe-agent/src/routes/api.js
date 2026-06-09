import { Router } from 'express';
import { apiKeyGuard } from '../middleware/apiKeyGuard.js';
import { createApiRateLimiter } from '../middleware/rateLimiter.js';
import { createLink, getLinkStats, deleteLink, resolveLink } from '../services/links.js';
import { z } from 'zod';
import { createHash, randomBytes } from 'crypto';
import bcryptjs from 'bcryptjs';

export function createApiRouter(prisma) {
  const router = Router();
  const apiGuard = apiKeyGuard(prisma);

  // Apply rate limiting and auth to all API routes
  router.use(apiGuard);

  // Dynamic rate limiter based on tier
  router.use(async (req, res, next) => {
    const user = req.user;
    const limit = user.tier === 'pro' ? 600 : 60;
    const limiter = createApiRateLimiter(limit);
    limiter(req, res, next);
  });

  // POST /api/v1/links
  router.post('/links', async (req, res) => {
    try {
      const { destinationUrl, customSlug, expiresAt, password } = req.body;

      // Validate URL
      if (!destinationUrl) {
        return res.status(400).json({
          error: { code: 'INVALID_URL', message: 'destinationUrl is required' }
        });
      }

      try {
        new URL(destinationUrl);
      } catch {
        return res.status(400).json({
          error: { code: 'INVALID_URL', message: 'Invalid URL format' }
        });
      }

      const link = await createLink(prisma, {
        destinationUrl,
        userId: req.user.id,
        customSlug,
        expiresAt,
        password,
        tier: req.user.tier
      });

      res.status(201).json({
        shortCode: link.shortCode,
        shortUrl: `${process.env.BASE_URL}/${link.shortCode}`,
        destinationUrl: link.destinationUrl,
        expiresAt: link.expiresAt ? link.expiresAt.toISOString() : null,
        createdAt: link.createdAt.toISOString()
      });
    } catch (err) {
      if (err.status) {
        return res.status(err.status).json({ error: { code: err.code, message: err.message } });
      }
      console.error('API create link error:', err);
      res.status(500).json({ error: { code: 'SERVER_ERROR', message: 'An error occurred' } });
    }
  });

  // GET /api/v1/links
  router.get('/links', async (req, res) => {
    try {
      const { page = '1', perPage = '20', status = 'all', sort = 'createdAt' } = req.query;
      const pageNum = Math.max(1, parseInt(page) || 1);
      const limit = Math.min(100, parseInt(perPage) || 20);

      let where = { userId: req.user.id, deletedAt: null };

      if (status === 'active') {
        where.OR = [{ expiresAt: null }, { expiresAt: { gt: new Date() } }];
      } else if (status === 'expired') {
        where.expiresAt = { lt: new Date() };
      }

      const links = await prisma.link.findMany({
        where,
        include: { clicks: { select: { id: true } } },
        orderBy: { [sort]: 'desc' },
        skip: (pageNum - 1) * limit,
        take: limit
      });

      const total = await prisma.link.count({ where });

      res.json({
        data: links.map(l => ({
          shortCode: l.shortCode,
          shortUrl: `${process.env.BASE_URL}/${l.shortCode}`,
          destinationUrl: l.destinationUrl,
          status: l.expiresAt && new Date() > l.expiresAt ? 'expired' : 'active',
          totalClicks: l.clicks.length,
          createdAt: l.createdAt.toISOString(),
          expiresAt: l.expiresAt ? l.expiresAt.toISOString() : null
        })),
        meta: { page: pageNum, perPage: limit, total }
      });
    } catch (err) {
      console.error('API list links error:', err);
      res.status(500).json({ error: { code: 'SERVER_ERROR', message: 'An error occurred' } });
    }
  });

  // GET /api/v1/links/:shortCode
  router.get('/links/:shortCode', async (req, res) => {
    try {
      const { shortCode } = req.params;
      const link = await prisma.link.findUnique({
        where: { shortCode },
        include: { clicks: { select: { id: true } } }
      });

      if (!link || link.userId !== req.user.id || link.deletedAt) {
        return res.status(404).json({
          error: { code: 'NOT_FOUND', message: 'Link not found' }
        });
      }

      res.json({
        shortCode: link.shortCode,
        shortUrl: `${process.env.BASE_URL}/${link.shortCode}`,
        destinationUrl: link.destinationUrl,
        totalClicks: link.clicks.length,
        createdAt: link.createdAt.toISOString(),
        expiresAt: link.expiresAt ? link.expiresAt.toISOString() : null
      });
    } catch (err) {
      console.error('API get link error:', err);
      res.status(500).json({ error: { code: 'SERVER_ERROR', message: 'An error occurred' } });
    }
  });

  // PATCH /api/v1/links/:shortCode
  router.patch('/links/:shortCode', async (req, res) => {
    try {
      const { shortCode } = req.params;
      const { destinationUrl, expiresAt, password } = req.body;

      const link = await prisma.link.findUnique({
        where: { shortCode }
      });

      if (!link || link.userId !== req.user.id || link.deletedAt) {
        return res.status(404).json({
          error: { code: 'NOT_FOUND', message: 'Link not found' }
        });
      }

      const data = {};
      if (destinationUrl) data.destinationUrl = destinationUrl;
      if (expiresAt !== undefined && req.user.tier === 'pro') {
        data.expiresAt = expiresAt ? new Date(expiresAt) : null;
      }

      const updated = await prisma.link.update({
        where: { shortCode },
        data
      });

      res.json({
        shortCode: updated.shortCode,
        destinationUrl: updated.destinationUrl,
        expiresAt: updated.expiresAt ? updated.expiresAt.toISOString() : null
      });
    } catch (err) {
      console.error('API update link error:', err);
      res.status(500).json({ error: { code: 'SERVER_ERROR', message: 'An error occurred' } });
    }
  });

  // DELETE /api/v1/links/:shortCode
  router.delete('/links/:shortCode', async (req, res) => {
    try {
      const { shortCode } = req.params;
      const link = await prisma.link.findUnique({
        where: { shortCode }
      });

      if (!link || link.userId !== req.user.id) {
        return res.status(404).json({
          error: { code: 'NOT_FOUND', message: 'Link not found' }
        });
      }

      await prisma.link.update({
        where: { shortCode },
        data: { deletedAt: new Date() }
      });

      res.json({ success: true });
    } catch (err) {
      console.error('API delete link error:', err);
      res.status(500).json({ error: { code: 'SERVER_ERROR', message: 'An error occurred' } });
    }
  });

  // GET /api/v1/links/:shortCode/stats
  router.get('/links/:shortCode/stats', async (req, res) => {
    try {
      const { shortCode } = req.params;
      const link = await prisma.link.findUnique({
        where: { shortCode }
      });

      if (!link || link.userId !== req.user.id || link.deletedAt) {
        return res.status(404).json({
          error: { code: 'NOT_FOUND', message: 'Link not found' }
        });
      }

      const stats = await getLinkStats(prisma, shortCode);
      res.json(stats);
    } catch (err) {
      console.error('API stats error:', err);
      res.status(500).json({ error: { code: 'SERVER_ERROR', message: 'An error occurred' } });
    }
  });

  // GET /api/v1/account
  router.get('/account', async (req, res) => {
    try {
      const user = await prisma.user.findUnique({
        where: { id: req.user.id }
      });

      const linkCount = await prisma.link.count({
        where: { userId: req.user.id, deletedAt: null }
      });

      res.json({
        id: user.id,
        email: user.email,
        tier: user.tier,
        quota: user.tier === 'free' ? { used: linkCount, limit: 50 } : { used: linkCount, limit: null }
      });
    } catch (err) {
      console.error('API account error:', err);
      res.status(500).json({ error: { code: 'SERVER_ERROR', message: 'An error occurred' } });
    }
  });

  return router;
}

// OpenAPI spec
export function getOpenApiSpec() {
  return {
    openapi: '3.0.0',
    info: { title: 'URL Shortener API', version: '1.0.0' },
    paths: {
      '/api/v1/links': {
        post: { summary: 'Create a short link', tags: ['Links'] },
        get: { summary: 'List user links', tags: ['Links'] }
      },
      '/api/v1/links/{shortCode}': {
        get: { summary: 'Get link details', tags: ['Links'] },
        patch: { summary: 'Update link', tags: ['Links'] },
        delete: { summary: 'Delete link', tags: ['Links'] }
      },
      '/api/v1/links/{shortCode}/stats': {
        get: { summary: 'Get link statistics', tags: ['Analytics'] }
      },
      '/api/v1/account': {
        get: { summary: 'Get account info', tags: ['Account'] }
      }
    }
  };
}
