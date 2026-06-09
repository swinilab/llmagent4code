import { createHash } from 'crypto';

export function apiKeyGuard(prisma) {
  return async (req, res, next) => {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Missing or invalid API key' } });
    }
    
    const rawKey = authHeader.slice(7);
    const keyHash = createHash('sha256').update(rawKey).digest('hex');
    
    try {
      const apiKey = await prisma.apiKey.findUnique({
        where: { keyHash },
        include: { user: true }
      });
      
      if (!apiKey || apiKey.revokedAt) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Invalid API key' } });
      }
      
      await prisma.apiKey.update({
        where: { id: apiKey.id },
        data: { lastUsedAt: new Date() }
      });
      
      req.user = apiKey.user;
      next();
    } catch (err) {
      return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Invalid API key' } });
    }
  };
}
