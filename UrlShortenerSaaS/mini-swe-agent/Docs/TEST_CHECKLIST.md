# Test Checklist

This document outlines how to verify all requirements from the SRS.

## Prerequisites
- Node.js 20 LTS installed
- npm installed
- Port 3000 available

## Setup

```bash
npm install
node server.js
```

The app will start on http://localhost:3000 and automatically create the database.

## Functional Requirements Testing

### FR-AUTH: Authentication
- [ ] Register new user: Go to `/register`, enter email + password (8+ chars, letter+digit)
- [ ] Login: Go to `/login`, enter credentials
- [ ] Logout: Click logout button
- [ ] Password reset: Click "Forgot password" on login page
- [ ] Login rate limit: Try logging in with wrong password 6 times (should be blocked)
- [ ] JWT cookie: Check DevTools → Application → Cookies for `auth_token`

### FR-SHORT: URL Shortening
- [ ] Create short link (guest): Submit URL on home page (no account required)
- [ ] Create short link (user): Login, create link from dashboard
- [ ] Custom slug (Pro): Try setting custom slug - should fail for free users
- [ ] Link expiry (Pro): Try setting expiry - should fail for free users
- [ ] Password protection (Pro): Try setting password - should fail for free users
- [ ] Quota limit (Free): Create 50 links, try to create 51st (should fail)

### FR-REDIR: Redirect Service
- [ ] 302 Redirect: Visit a short URL, check HTTP status
- [ ] 404 Error: Visit non-existent short code
- [ ] 410 Error: Create link with expiry, wait for expiry, visit
- [ ] Password gate: Create password-protected link, visit without password (should show form)
- [ ] Unlock: Enter correct password (should redirect)
- [ ] Click recording: Create link, visit it 5 times, check stats
- [ ] Cache: Visit same link twice, second should be from cache

### FR-MGMT: Link Management
- [ ] Dashboard list: Login, go to `/dashboard`
- [ ] Sorting: Try sort by createdAt, clicks, slug
- [ ] Filtering: Try filter by active/expired/all
- [ ] Search: Search by short code
- [ ] Edit link: Update destination URL
- [ ] Delete link: Soft delete a link (should return 404)
- [ ] Pagination: Create many links, check pagination

### FR-ANAL: Analytics
- [ ] View stats: Click "Stats" button on any link
- [ ] Daily clicks: Should show last 30 days
- [ ] Referrers: Visit from different referrer, check stats
- [ ] Device type: Visit from different user agents, check breakdown
- [ ] CSV export (Pro): Pro users should see download button
- [ ] Unique clicks: Should be ≤ total clicks

### FR-QR: QR Codes
- [ ] Generate QR: Go to link stats, check QR code image
- [ ] Scan QR: Scan with phone camera
- [ ] Download QR: Click download button

### FR-API: REST API
- [ ] GET /api/v1/openapi.json: View OpenAPI spec
- [ ] Create link: POST /api/v1/links with valid JSON
- [ ] Invalid auth: Try without API key (should get 401)
- [ ] Rate limit: Make 61+ requests as free user in 60s (should get 429)
- [ ] List links: GET /api/v1/links
- [ ] Get link: GET /api/v1/links/{shortCode}
- [ ] Update link: PATCH /api/v1/links/{shortCode}
- [ ] Delete link: DELETE /api/v1/links/{shortCode}
- [ ] Get stats: GET /api/v1/links/{shortCode}/stats
- [ ] Get account: GET /api/v1/account

### FR-TIER: Subscription Tiers
- [ ] Free tier: Max 50 links, no custom slug, no expiry
- [ ] Pro upgrade: Send webhook to /internal/billing/upgrade
- [ ] Pro features: After upgrade, custom slug should work
- [ ] Usage bar: Dashboard should show "X / 50 links"

## Non-Functional Requirements Testing

### NFR-PERF: Performance
- [ ] Redirect latency: Visit short URL, should be < 100ms
- [ ] Homepage load: Should be < 5s
- [ ] Dashboard load: Should be < 5s
- [ ] API create link: Should be < 400ms

### NFR-AVAIL: Availability
- [ ] Health endpoint: curl http://localhost:3000/health
- [ ] Should return: `{"status":"ok","db":"ok"}`
- [ ] Kill server: `kill -9 <pid>`
- [ ] Restart: `node server.js`
- [ ] Previous links: Visit old short codes, should still redirect

### NFR-SEC: Security
- [ ] Security headers: Check response headers for X-Content-Type-Options, X-Frame-Options, CSP
- [ ] Password hash: Query DB, passwords should start with `$2b$`
- [ ] API rate limit: 65 requests as free user in 60s, should get 429
- [ ] Protected routes: Visit /dashboard without login (should redirect to /login)
- [ ] API protected: GET /api/v1/account without token (should return 401)

### NFR-USE: Usability
- [ ] 3 interactions: Login → create link → copy URL (3 clicks max)
- [ ] Mobile layout: Open in 375px viewport, no horizontal scroll
- [ ] Form errors: Invalid form submit should show error without reload

### NFR-DATA: Data Integrity
- [ ] Unique codes: 500+ links, no duplicates
- [ ] Click count: Manual count vs API response should match

### NFR-MAINT: Maintainability
- [ ] Tests: `npm test` should pass
- [ ] Linter: `npm run lint` should pass with 0 errors

## Manual Feature Verification

### User Journey 1: Guest Shortening
1. Open http://localhost:3000
2. Enter any long URL
3. Click "Shorten"
4. Copy short URL
5. Paste in new tab
6. Should redirect to original URL

### User Journey 2: Free User
1. Click "Register"
2. Enter email + password
3. Create 5 short links
4. Go to Dashboard
5. Click Stats on one link
6. Visit the link multiple times
7. Refresh stats page, click count should increase

### User Journey 3: Pro User
1. Follow User Journey 2
2. Open new terminal: `curl -X POST http://localhost:3000/internal/billing/upgrade -H "X-Webhook-Secret: webhook_secret" -H "Content-Type: application/json" -d '{"userId": "USERID", "newTier": "pro"}'` (find userId in Prisma Studio)
3. Refresh page, should see Pro badge
4. Create new link with custom slug "my-link"
5. Set expiry date
6. Verify custom slug works: http://localhost:3000/my-link
7. Visit Stats, should see "Download CSV" button

### User Journey 4: API Usage
1. Login and go to Account settings
2. Click "Generate New Key"
3. Copy the raw key
4. Open terminal and run:
```bash
curl -X POST http://localhost:3000/api/v1/links \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"destinationUrl":"https://google.com"}'
```
5. Should return created link with short code

## Docker Testing

```bash
docker compose up
# Wait for "Server running at http://localhost:3000"
# Run same tests as above
```

## Database Verification

```bash
npx prisma studio
# Browse tables:
# - User: Check passwordHash starts with $2b$
# - Link: Check shortCode uniqueness
# - ClickEvent: Check click recording
# - ApiKey: Check keyHash is SHA-256
# - PasswordResetToken: Check tokenHash
```

## Performance Benchmarking

### Redirect Performance
```bash
# First, create a short link and note its code
curl -s "http://localhost:3000/abc123" -I -w "Time: %{time_total}s\n"
# Run 10 times, average should be < 100ms
```

## Sign-off

When all tests pass:
- [ ] Functional requirements: All working
- [ ] Non-functional requirements: All measurable
- [ ] Code quality: Lint passes, no console errors
- [ ] Performance: Acceptable latency
- [ ] Security: Headers present, passwords hashed
- [ ] Data integrity: No corruption, clicks accurate
- [ ] Usability: Works as expected
- [ ] Docker: Container runs correctly
- [ ] API: All endpoints functional

**Date Tested:** ___________
**Tester:** ___________
**Result:** ✅ PASS / ❌ FAIL
