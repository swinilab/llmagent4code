import { Router } from 'express';
import bcryptjs from 'bcryptjs';
import { resolveLink, recordClick } from '../services/links.js';

export function createRedirectRouter(prisma, cache) {
  const router = Router();

  router.get('/:shortCode', async (req, res) => {
    try {
      const { shortCode } = req.params;

      // Check cache first
      let link = cache.get(shortCode);
      
      if (!link) {
        const result = await resolveLink(prisma, shortCode);
        if (!result.found) {
          if (result.expired) {
            return res.status(410).render('expired');
          }
          return res.status(404).render('404');
        }
        link = result.link;
        cache.set(shortCode, link);
      }

      // Check password
      if (link.passwordHash) {
        return res.render('password-gate', { shortCode });
      }

      // Record click (non-blocking)
      setImmediate(async () => {
        try {
          await recordClick(prisma, link.id, {
            ipAddress: req.ip,
            userAgent: req.headers['user-agent'],
            referrer: req.headers.referer
          });
        } catch (err) {
          console.error('Click recording error:', err);
        }
      });

      res.redirect(302, link.destinationUrl);
    } catch (err) {
      console.error('Redirect error:', err);
      res.status(500).render('error', { error: 'An error occurred' });
    }
  });

  router.post('/:shortCode/unlock', async (req, res) => {
    try {
      const { shortCode } = req.params;
      const { password } = req.body;

      const link = await prisma.link.findUnique({
        where: { shortCode }
      });

      if (!link || link.deletedAt) {
        return res.status(404).render('404');
      }

      if (!link.passwordHash || !(await bcryptjs.compare(password, link.passwordHash))) {
        return res.render('password-gate', { shortCode, error: 'Invalid password' });
      }

      // Set cookie to allow redirect
      res.cookie(`unlock_${shortCode}`, '1', { httpOnly: true, maxAge: 60 * 60 * 1000 });

      // Record click
      setImmediate(async () => {
        try {
          await recordClick(prisma, link.id, {
            ipAddress: req.ip,
            userAgent: req.headers['user-agent'],
            referrer: req.headers.referer
          });
        } catch (err) {
          console.error('Click recording error:', err);
        }
      });

      res.redirect(302, link.destinationUrl);
    } catch (err) {
      console.error('Unlock error:', err);
      res.status(500).render('error', { error: 'An error occurred' });
    }
  });

  return router;
}
