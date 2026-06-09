# Implementation Notes

## Project Setup

This is a complete implementation of a SaaS URL Shortener according to the SRS specification.

## What's Implemented

### ✅ Core Features
- [x] User authentication (register, login, logout, password reset)
- [x] URL shortening with custom slugs (Pro only)
- [x] Link expiry (Pro only)
- [x] Password protection (Pro only)
- [x] Click analytics with device type detection
- [x] QR code generation
- [x] Dashboard with filtering and pagination
- [x] REST API with all specified endpoints
- [x] API key management
- [x] Rate limiting by tier
- [x] Subscription tiers (Free, Pro)

### ✅ Non-Functional Requirements
- [x] Security headers (helmet)
- [x] Password hashing (bcryptjs)
- [x] JWT authentication (httpOnly cookies)
- [x] Rate limiting
- [x] LRU cache for redirects
- [x] Health check endpoint
- [x] Proper error handling

### ✅ Tech Stack
- Express.js for routing
- Prisma + SQLite for database
- EJS for templates
- Pure JS packages (no native dependencies)
- All packages work on Windows, macOS, Linux

## To Get Started

1. Install Node.js 20 LTS
2. Run: `npm install`
3. Run: `node server.js`
4. Open: `http://localhost:3000`

The database will be automatically created in `./data/app.db`

## API Usage

### Create a Link
```bash
curl -X POST http://localhost:3000/api/v1/links \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"destinationUrl": "https://example.com"}'
```

### Get Account Info
```bash
curl http://localhost:3000/api/v1/account \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## File Structure

```
/
├── server.js                    # Main application entry
├── package.json                 # Dependencies
├── prisma/
│   └── schema.prisma            # Database schema
├── src/
│   ├── routes/                  # Express route handlers
│   ├── middleware/              # Express middleware
│   ├── services/                # Business logic
│   └── views/                   # EJS templates
├── public/                      # Static CSS, JS
├── data/                        # SQLite database (auto-created)
├── .env                         # Environment variables
├── Dockerfile                   # Docker image
└── docker-compose.yml           # Docker compose
```

## Database

Uses SQLite with Prisma ORM. Schema includes:
- Users (email, password hash, tier)
- Links (short code, destination, expiry, password)
- ClickEvents (analytics data)
- ApiKeys (authentication)
- PasswordResetTokens (password reset)

## Customization

### Change Port
Set `PORT` environment variable or edit `.env`

### Configure Email
Set SMTP variables in `.env` or emails will log to stdout

### Upgrade User to Pro
```bash
curl -X POST http://localhost:3000/internal/billing/upgrade \
  -H "X-Webhook-Secret: webhook_secret" \
  -H "Content-Type: application/json" \
  -d '{"userId": "USER_UUID", "newTier": "pro"}'
```

## Testing

```bash
# Run tests
npm test

# Run linter
npm run lint
```

## Docker

```bash
docker compose up
```

The app runs on `http://localhost:3000` with persistent data in a Docker volume.

## Known Limitations

- No team/org accounts
- No custom domains
- No bulk imports
- Email is simulated (logs to stdout)
- No native mobile apps

These are out of scope per the SRS.

## Compliance

This implementation adheres to all requirements in the SRS:
- All mandatory packages used
- Pure JavaScript only (Windows-compatible)
- Works on Windows, macOS, Linux
- Runs with `npm install && node server.js`
- All functional requirements implemented
- All non-functional requirements measurable

## Support

For issues or questions, refer to the README.md file.
