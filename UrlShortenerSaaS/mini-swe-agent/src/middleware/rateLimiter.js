import rateLimit from 'express-rate-limit';

export const loginLimiter = rateLimit({
  windowMs: 10 * 60 * 1000,
  max: 5,
  message: 'Too many login attempts, please try again later.',
  standardHeaders: false,
  legacyHeaders: false,
  keyGenerator: (req) => req.ip
});

export const generalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: false,
  legacyHeaders: false
});

export function createApiRateLimiter(limitsPerMinute = 60) {
  return rateLimit({
    windowMs: 60 * 1000,
    max: limitsPerMinute,
    standardHeaders: false,
    legacyHeaders: false,
    keyGenerator: (req) => req.user?.id || req.ip,
    skip: (req) => !req.user,
    handler: (req, res) => {
      res.status(429).json({ 
        error: { code: 'RATE_LIMIT_EXCEEDED', message: 'Too many requests' } 
      });
    }
  });
}
