import { Router } from 'express';
import { authGuard } from '../middleware/authGuard.js';
import { createLink, getLinkStats, deleteLink, recordClick, resolveLink } from '../services/links.js';
import { generateQR } from '../services/qr.js';
import { z } from 'zod';

export function createLinksRouter(prisma) {
  const router = Router();

  router.get('/dashboard', authGuard, async (req, res) => {
    try {
      const { page = '1', sort = 'createdAt', status = 'all', q = '' } = req.query;
      const pageNum = Math.max(1, parseInt(page) || 1);
      const perPage = 20;

      let where = { userId: req.user.id, deletedAt: null };

      if (q) {
        where = {
          ...where,
          OR: [
            { shortCode: { contains: q } },
            { destinationUrl: { contains: q } }
          ]
        };
      }

      if (status === 'active') {
        where = { ...where, OR: [{ expiresAt: null }, { expiresAt: { gt: new Date() } }] };
      } else if (status === 'expired') {
        where = { ...where, expiresAt: { lt: new Date() } };
      }

      const links = await prisma.link.findMany({
        where,
        include: { clicks: { select: { id: true } } },
        orderBy: {
          [sort === 'clicks' ? 'clicks' : sort]: sort === 'clicks' ? { _count: 'desc' } : 'desc'
        },
        skip: (pageNum - 1) * perPage,
        take: perPage
      });

      const total = await prisma.link.count({ where });

      const user = await prisma.user.findUnique({
        where: { id: req.user.id }
      });

      const activeCount = await prisma.link.count({
        where: { userId: req.user.id, deletedAt: null }
      });

      res.render('dashboard', {
        user,
        links: links.map(l => ({
          ...l,
          totalClicks: l.clicks.length,
          status: l.expiresAt && new Date() > l.expiresAt ? 'Expired' : 'Active'
        })),
        page: pageNum,
        perPage,
        total,
        sort,
        status,
        q,
        quota: user.tier === 'free' ? `${activeCount} / 50` : 'Unlimited'
      });
    } catch (err) {
      console.error('Dashboard error:', err);
      res.status(500).render('error', { error: 'Failed to load dashboard' });
    }
  });

  router.get('/links/:shortCode/edit', authGuard, async (req, res) => {
    try {
      const { shortCode } = req.params;
      const link = await prisma.link.findUnique({
        where: { shortCode }
      });

      if (!link || link.userId !== req.user.id || link.deletedAt) {
        return res.status(404).render('404');
      }

      const user = await prisma.user.findUnique({ where: { id: req.user.id } });

      res.render('link-edit', { link, user });
    } catch (err) {
      console.error('Edit link error:', err);
      res.status(500).render('error', { error: 'Failed to load link' });
    }
  });

  router.post('/links/:shortCode/edit', authGuard, async (req, res) => {
    try {
      const { shortCode } = req.params;
      const { destinationUrl, expiresAt, password } = req.body;

      const link = await prisma.link.findUnique({
        where: { shortCode }
      });

      if (!link || link.userId !== req.user.id || link.deletedAt) {
        return res.status(404).render('404');
      }

      const data = {};
      if (destinationUrl) data.destinationUrl = destinationUrl;
      if (req.user.tier === 'pro') {
        if (expiresAt) data.expiresAt = new Date(expiresAt);
      }

      await prisma.link.update({
        where: { shortCode },
        data
      });

      res.redirect(`/links/${shortCode}/edit`);
    } catch (err) {
      console.error('Update link error:', err);
      res.status(500).render('error', { error: 'Failed to update link' });
    }
  });

  router.post('/links/:shortCode/delete', authGuard, async (req, res) => {
    try {
      const { shortCode } = req.params;
      const link = await prisma.link.findUnique({
        where: { shortCode }
      });

      if (!link || link.userId !== req.user.id) {
        return res.status(404).render('404');
      }

      await prisma.link.update({
        where: { shortCode },
        data: { deletedAt: new Date() }
      });

      res.redirect('/dashboard');
    } catch (err) {
      console.error('Delete link error:', err);
      res.status(500).render('error', { error: 'Failed to delete link' });
    }
  });

  router.get('/links/:shortCode/stats', authGuard, async (req, res) => {
    try {
      const { shortCode } = req.params;
      const link = await prisma.link.findUnique({
        where: { shortCode }
      });

      if (!link || link.userId !== req.user.id || link.deletedAt) {
        return res.status(404).render('404');
      }

      const stats = await getLinkStats(prisma, shortCode);
      const user = await prisma.user.findUnique({ where: { id: req.user.id } });

      res.render('link-stats', { link, stats, user });
    } catch (err) {
      console.error('Stats error:', err);
      res.status(500).render('error', { error: 'Failed to load stats' });
    }
  });

  router.get('/links/:shortCode/qr', async (req, res) => {
    try {
      const { shortCode } = req.params;
      const shortUrl = `${process.env.BASE_URL}/${shortCode}`;
      const buffer = await generateQR(shortUrl);
      res.contentType('image/png');
      res.send(buffer);
    } catch (err) {
      console.error('QR error:', err);
      res.status(500).send('Failed to generate QR code');
    }
  });

  router.get('/links/:shortCode/stats/export', authGuard, async (req, res) => {
    try {
      const { shortCode } = req.params;
      const link = await prisma.link.findUnique({
        where: { shortCode },
        include: { clicks: true }
      });

      if (!link || link.userId !== req.user.id || link.deletedAt) {
        return res.status(404).render('404');
      }

      if (req.user.tier !== 'pro') {
        return res.status(403).render('error', { error: 'Feature available for Pro users only' });
      }

      const csv = [
        'timestamp,ipAddress,deviceType,referrer',
        ...link.clicks.map(c => 
          `"${c.clickedAt.toISOString()}","${c.ipAddress || ''}","${c.deviceType || ''}","${(c.referrer || '').replace(/"/g, '""')}"`
        )
      ].join('\n');

      res.contentType('text/csv');
      res.attachment(`stats-${shortCode}.csv`);
      res.send(csv);
    } catch (err) {
      console.error('Export error:', err);
      res.status(500).send('Failed to export stats');
    }
  });

  return router;
}
