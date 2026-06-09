# SaaS URL Shortener

A modern URL shortening service with analytics, custom slugs, password protection, and API access.

**Agent:** mini-swe-agent v2.3.0

**LLM:** Claude Haiku 4.5

## Features

- **Free Tier**: 50 active links, basic analytics, 1 API key
- **Pro Tier**: Unlimited links, custom slugs, link expiry, password protection, CSV export, 5 API keys
- **Dashboard**: Manage all your short links with detailed analytics
- **REST API**: Programmatic access to all features
- **QR Codes**: Generate and download QR codes for each link
- **Analytics**: Track clicks, referrers, device types, and more

## Prerequisites

- Node.js 20 LTS or higher
- npm

## Quick Start

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set up Prisma backend**:
   ```bash
   npx prisma migrate deploy
   ```

3. **Run the application**:
   ```bash
   node server.js
   ```

4. **Access the app**:
   Open `http://localhost:3000` in your browser.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `3000` |
| `BASE_URL` | Application base URL | `http://localhost:3000` |
| `JWT_SECRET` | Secret for JWT signing | `change_me_in_production` |
| `DATABASE_URL` | SQLite database path | `file:./data/app.db` |
| `BILLING_WEBHOOK_SECRET` | Webhook secret for upgrades | `webhook_secret` |
| `SMTP_HOST` | SMTP server host (optional) | (logs to stdout if unset) |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | |
| `SMTP_PASS` | SMTP password | |
| `SMTP_FROM` | Email from address | `noreply@example.com` |

## API Documentation

Base URL: `/api/v1/`

### Authentication

All API endpoints require an API key in the Authorization header:

```
Authorization: Bearer your_api_key_here
```

Generate API keys in your account settings.

### Endpoints

#### Create Short Link
```
POST /api/v1/links
Content-Type: application/json

{
  "destinationUrl": "https://example.com/long/url",
  "customSlug": "my-link",        // Pro only
  "expiresAt": "2026-12-31T23:59:59Z",  // Pro only
  "password": "secret"            // Pro only
}

Response (201):
{
  "shortCode": "abc123",
  "shortUrl": "http://localhost:3000/abc123",
  "destinationUrl": "https://example.com/long/url",
  "expiresAt": null,
  "createdAt": "2026-06-08T10:00:00.000Z"
}
```

#### List Links
```
GET /api/v1/links?page=1&perPage=20&status=active&sort=createdAt

Response (200):
{
  "data": [...],
  "meta": { "page": 1, "perPage": 20, "total": 42 }
}
```

#### Get Link Statistics
```
GET /api/v1/links/{shortCode}/stats

Response (200):
{
  "shortCode": "abc123",
  "totalClicks": 100,
  "uniqueClicks": 85,
  "clicksByDay": [...],
  "topReferrers": [...],
  "byDevice": { "mobile": 60, "desktop": 40, "bot": 0, "unknown": 0 }
}
```

#### Get Account Info
```
GET /api/v1/account

Response (200):
{
  "id": "uuid",
  "email": "user@example.com",
  "tier": "free",
  "quota": { "used": 23, "limit": 50 }
}
```

### Rate Limits

- Free tier: 60 requests per minute
- Pro tier: 600 requests per minute

## Testing

Run tests with coverage:
```bash
npm test
```

Run linter:
```bash
npm run lint
```

## Simulating Pro Upgrade

To test Pro features locally, send a webhook request:

```bash
curl -X POST http://localhost:3000/internal/billing/upgrade \
  -H "X-Webhook-Secret: webhook_secret" \
  -H "Content-Type: application/json" \
  -d '{"userId": "YOUR_USER_ID", "newTier": "pro"}'
```

Find your user ID in the database using:
```bash
npx prisma studio
```

## Docker

Run with Docker Compose:
```bash
docker compose up
```

The app will be available at `http://localhost:3000`.

## Architecture

### Tech Stack

- **Backend**: Express.js (Node.js 20)
- **Database**: SQLite + Prisma ORM
- **Frontend**: EJS templates + Vanilla JavaScript
- **Authentication**: JWT (httpOnly cookies)
- **Password Hashing**: bcryptjs
- **Security**: helmet.js
- **Caching**: LRU Cache (in-process redirects)
- **Rate Limiting**: express-rate-limit
- **QR Codes**: qrcode

### Database Models

- **User**: Email, password hash, tier (free/pro)
- **Link**: Short code, destination URL, optional password/expiry
- **ClickEvent**: Analytics data (IP, user-agent, referrer, device type)
- **ApiKey**: Authentication tokens for API access
- **PasswordResetToken**: One-time reset tokens

## Security

- Passwords hashed with bcryptjs (cost factor 10)
- API keys stored as SHA-256 hashes
- JWT tokens in httpOnly cookies (7-day expiry)
- Rate limiting on login (5 attempts per 10 minutes)
- Helmet.js for security headers
- CSRF protection via SameSite cookies
- SQL injection protection via Prisma

## Performance

- LRU cache for frequent redirects (1000 entries, 1-hour TTL)
- Non-blocking click recording via setImmediate
- Database indexes on frequently queried fields
- Lighthouse performance score ≥ 70

## Troubleshooting

### Database locked
If you see a "database is locked" error:
1. Stop the server
2. Delete the `.db-wal` and `.db-shm` files in the `data/` folder
3. Restart the server

### Port already in use
Change the PORT environment variable:
```bash
PORT=3001 node server.js
```

### SMTP not working
Leave `SMTP_HOST` empty to log emails to stdout:
```
SMTP_HOST=
