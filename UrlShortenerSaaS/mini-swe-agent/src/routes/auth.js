import { Router } from 'express';
import bcryptjs from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { loginLimiter } from '../middleware/rateLimiter.js';
import { sendMail } from '../services/email.js';
import { createHash, randomBytes } from 'crypto';

export function createAuthRouter(prisma) {
  const router = Router();

  const emailSchema = z.string().email();
  const passwordSchema = z.string().min(8).regex(/[a-zA-Z]/).regex(/\d/);

  router.get('/register', (req, res) => {
    res.render('register');
  });

  router.post('/register', async (req, res) => {
    try {
      const { email, password } = req.body;

      // Validate
      emailSchema.parse(email);
      passwordSchema.parse(password);

      // Check existing
      const existing = await prisma.user.findUnique({ where: { email } });
      if (existing) {
        return res.render('register', { error: 'Email already registered' });
      }

      // Create user
      const hash = await bcryptjs.hash(password, 10);
      const user = await prisma.user.create({
        data: { email, passwordHash: hash, tier: 'free' }
      });

      // Create default API key
      const rawKey = randomBytes(32).toString('hex');
      const keyHash = createHash('sha256').update(rawKey).digest('hex');
      await prisma.apiKey.create({
        data: {
          userId: user.id,
          keyHash,
          label: 'Default'
        }
      });

      // Create JWT
      const token = jwt.sign({ id: user.id, email: user.email, tier: user.tier }, process.env.JWT_SECRET, {
        expiresIn: '7d'
      });

      res.cookie('auth_token', token, { httpOnly: true, maxAge: 7 * 24 * 60 * 60 * 1000 });
      res.redirect('/dashboard');
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.render('register', { error: 'Invalid email or password' });
      }
      console.error('Register error:', err);
      res.render('register', { error: 'Registration failed' });
    }
  });

  router.get('/login', (req, res) => {
    res.render('login');
  });

  router.post('/login', loginLimiter, async (req, res) => {
    try {
      const { email, password } = req.body;

      const user = await prisma.user.findUnique({ where: { email } });
      if (!user) {
        return res.render('login', { error: 'Invalid credentials' });
      }

      const match = await bcryptjs.compare(password, user.passwordHash);
      if (!match) {
        return res.render('login', { error: 'Invalid credentials' });
      }

      const token = jwt.sign({ id: user.id, email: user.email, tier: user.tier }, process.env.JWT_SECRET, {
        expiresIn: '7d'
      });

      res.cookie('auth_token', token, { httpOnly: true, maxAge: 7 * 24 * 60 * 60 * 1000 });
      res.redirect('/dashboard');
    } catch (err) {
      console.error('Login error:', err);
      res.render('login', { error: 'Login failed' });
    }
  });

  router.post('/logout', (req, res) => {
    res.clearCookie('auth_token');
    res.redirect('/');
  });

  router.get('/forgot-password', (req, res) => {
    res.render('forgot-password');
  });

  router.post('/forgot-password', async (req, res) => {
    try {
      const { email } = req.body;
      const user = await prisma.user.findUnique({ where: { email } });

      if (user) {
        const token = randomBytes(32).toString('hex');
        const tokenHash = createHash('sha256').update(token).digest('hex');
        const expiresAt = new Date(Date.now() + 60 * 60 * 1000);

        await prisma.passwordResetToken.create({
          data: { userId: user.id, tokenHash, expiresAt }
        });

        const resetUrl = `${process.env.BASE_URL}/auth/reset-password?token=${token}`;
        await sendMail(
          email,
          'Password Reset',
          `<p>Click <a href="${resetUrl}">here</a> to reset your password</p>`,
          `Reset your password: ${resetUrl}`
        );
      }

      res.render('forgot-password', { message: 'If account exists, reset link was sent' });
    } catch (err) {
      console.error('Forgot password error:', err);
      res.render('forgot-password', { error: 'An error occurred' });
    }
  });

  router.get('/reset-password', (req, res) => {
    const { token } = req.query;
    res.render('reset-password', { token });
  });

  router.post('/reset-password', async (req, res) => {
    try {
      const { token, password } = req.body;

      passwordSchema.parse(password);

      const tokenHash = createHash('sha256').update(token).digest('hex');
      const resetToken = await prisma.passwordResetToken.findUnique({
        where: { tokenHash }
      });

      if (!resetToken || new Date() > resetToken.expiresAt || resetToken.usedAt) {
        return res.render('reset-password', { token, error: 'Invalid or expired token' });
      }

      const hash = await bcryptjs.hash(password, 10);
      await prisma.user.update({
        where: { id: resetToken.userId },
        data: { passwordHash: hash }
      });

      await prisma.passwordResetToken.update({
        where: { id: resetToken.id },
        data: { usedAt: new Date() }
      });

      res.render('reset-password', { message: 'Password reset successful. Please login.' });
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.render('reset-password', { error: 'Password does not meet requirements' });
      }
      console.error('Reset password error:', err);
      res.render('reset-password', { error: 'An error occurred' });
    }
  });

  return router;
}
