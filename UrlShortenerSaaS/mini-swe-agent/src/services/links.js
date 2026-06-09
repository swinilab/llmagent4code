import { nanoid } from 'nanoid';
import bcryptjs from 'bcryptjs';

const ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

export async function generateShortCode(prisma, maxAttempts = 10) {
  for (let i = 0; i < maxAttempts; i++) {
    const code = nanoid(6, ALPHABET);
    const existing = await prisma.link.findUnique({
      where: { shortCode: code }
    });
    if (!existing) {
      return code;
    }
  }
  throw new Error('Failed to generate unique short code');
}

export async function createLink(prisma, {
  destinationUrl,
  userId = null,
  customSlug = null,
  expiresAt = null,
  password = null,
  tier = 'free'
}) {
  // Validate Pro features
  if (tier === 'free') {
    if (customSlug || expiresAt || password) {
      throw { code: 'PRO_FEATURE_ONLY', message: 'This feature is only available for Pro users', status: 403 };
    }
  }

  // Check custom slug
  let shortCode = customSlug;
  if (customSlug) {
    const existing = await prisma.link.findUnique({
      where: { shortCode: customSlug }
    });
    if (existing) {
      throw { code: 'SLUG_TAKEN', message: 'Custom slug already taken', status: 409 };
    }
  } else {
    shortCode = await generateShortCode(prisma);
  }

  // Check quota for free users
  if (tier === 'free' && userId) {
    const count = await prisma.link.count({
      where: { userId, deletedAt: null }
    });
    if (count >= 50) {
      throw { code: 'QUOTA_EXCEEDED', message: 'Free tier limited to 50 active links', status: 422 };
    }
  }

  // Hash password if provided
  let passwordHash = null;
  if (password) {
    passwordHash = await bcryptjs.hash(password, 10);
  }

  const link = await prisma.link.create({
    data: {
      shortCode,
      destinationUrl,
      userId,
      expiresAt: expiresAt ? new Date(expiresAt) : null,
      passwordHash
    }
  });

  return link;
}

export async function resolveLink(prisma, shortCode) {
  const link = await prisma.link.findUnique({
    where: { shortCode }
  });

  if (!link) {
    return { found: false };
  }

  if (link.deletedAt) {
    return { found: false };
  }

  if (link.expiresAt && new Date() > link.expiresAt) {
    return { found: false, expired: true };
  }

  return { found: true, link };
}

export async function getLinkStats(prisma, shortCode) {
  const link = await prisma.link.findUnique({
    where: { shortCode },
    include: { clicks: true }
  });

  if (!link) {
    throw new Error('Link not found');
  }

  const totalClicks = link.clicks.length;
  
  // Calculate unique clicks (distinct IP per 24-hour window)
  const dailyIps = new Map();
  link.clicks.forEach(click => {
    const day = click.clickedAt.toISOString().split('T')[0];
    const key = `${day}:${click.ipAddress}`;
    dailyIps.set(key, true);
  });
  const uniqueClicks = dailyIps.size;

  // Clicks by day (last 30 days)
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const clicksByDay = {};
  for (let i = 0; i < 30; i++) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    clicksByDay[date.toISOString().split('T')[0]] = 0;
  }

  link.clicks.forEach(click => {
    const day = click.clickedAt.toISOString().split('T')[0];
    if (clicksByDay.hasOwnProperty(day)) {
      clicksByDay[day]++;
    }
  });

  const clicksByDayArray = Object.entries(clicksByDay)
    .reverse()
    .map(([date, count]) => ({ date, count }));

  // Top referrers
  const referrers = {};
  link.clicks.forEach(click => {
    if (click.referrer) {
      try {
        const url = new URL(click.referrer);
        const domain = url.hostname;
        referrers[domain] = (referrers[domain] || 0) + 1;
      } catch {
        // Skip invalid referrers
      }
    }
  });

  const topReferrers = Object.entries(referrers)
    .map(([domain, count]) => ({ domain, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  // Device type breakdown
  const byDevice = {
    mobile: 0,
    desktop: 0,
    bot: 0,
    unknown: 0
  };

  link.clicks.forEach(click => {
    const type = click.deviceType || 'unknown';
    if (byDevice.hasOwnProperty(type)) {
      byDevice[type]++;
    }
  });

  return {
    shortCode,
    totalClicks,
    uniqueClicks,
    clicksByDay: clicksByDayArray,
    topReferrers,
    byDevice
  };
}

export async function updateLink(prisma, shortCode, userId, updates) {
  const link = await prisma.link.findUnique({
    where: { shortCode }
  });

  if (!link || link.userId !== userId) {
    throw { code: 'NOT_FOUND', message: 'Link not found', status: 404 };
  }

  const data = {};
  if (updates.destinationUrl) data.destinationUrl = updates.destinationUrl;
  if (updates.expiresAt !== undefined) data.expiresAt = updates.expiresAt;

  const updated = await prisma.link.update({
    where: { shortCode },
    data
  });

  return updated;
}

export async function deleteLink(prisma, shortCode, userId) {
  const link = await prisma.link.findUnique({
    where: { shortCode }
  });

  if (!link || link.userId !== userId) {
    throw { code: 'NOT_FOUND', message: 'Link not found', status: 404 };
  }

  await prisma.link.update({
    where: { shortCode },
    data: { deletedAt: new Date() }
  });
}

export async function recordClick(prisma, linkId, { ipAddress, userAgent, referrer }) {
  // Classify device type
  let deviceType = 'unknown';
  if (userAgent) {
    const ua = userAgent.toLowerCase();
    if (/bot|crawler|spider|crawling/i.test(ua)) {
      deviceType = 'bot';
    } else if (/mobile|android|iphone|ipad|windows phone/i.test(ua)) {
      deviceType = 'mobile';
    } else if (/windows|mac|linux|x11/i.test(ua)) {
      deviceType = 'desktop';
    }
  }

  await prisma.clickEvent.create({
    data: {
      linkId,
      ipAddress,
      userAgent,
      referrer,
      deviceType,
      clickedAt: new Date()
    }
  });
}
