# API Endpoints Reference

Documented from the active routes mounted in `src/app.ts` on 2026-03-19.

This file includes only active endpoints. Commented routes and `*.backup` files are intentionally excluded.

## Base URL

- Local default: `http://localhost:3000`
- JSON requests should use header: `Content-Type: application/json`

## Response formats

Most module endpoints use this envelope:

```json
{
  "success": true,
  "data": {},
  "message": "..."
}
```

Error responses usually look like this:

```json
{
  "success": false,
  "message": "...",
  "error": "..."
}
```

Known exceptions:

- `GET /token/:tenantId` returns `{ "token": "..." }`
- `GET /admin/auth/google/:tenantId` responds with an HTTP redirect to Google
- `GET /admin/auth/callback` responds with HTML
- `GET /admin/auth/status/:tenantId` returns plain JSON without the standard envelope
- `POST /admin/auth/refresh/:tenantId` returns plain JSON without the standard envelope
- Endpoints behind `tenantMiddleware` return plain text for some tenant errors:
  - `400 Tenant ID requerido`
  - `401 Tenand no existente`

## Authentication and required headers

### 1. Tenant-aware public routes

These routes require:

- `tenant_id: <TENANT_ID>`

They use `tenantMiddleware`, which also expects the tenant to already have Google OAuth tokens saved. In practice, the tenant must complete the admin Google setup first.

### 2. Protected user routes

These routes require:

- `Authorization: Bearer <ACCESS_TOKEN>`
- `tenant_id: <TENANT_ID>`

Important: several protected controllers still validate `tenant_id` from the header even though the JWT also contains the tenant.

### 3. Admin setup routes

These routes do not require JWT auth. The tenant is provided in the URL path or callback query string.

## Quick index

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/token/:tenantId` | None | Generate client JWT token |
| GET | `/admin/auth/google/:tenantId` | None | Start Google OAuth setup |
| GET | `/admin/auth/callback` | None | Google OAuth callback |
| GET | `/admin/auth/status/:tenantId` | None | Check Google auth setup status |
| POST | `/admin/auth/refresh/:tenantId` | None | Refresh saved Google tokens |
| POST | `/api/auth/register` | `tenant_id` | Register a portal user |
| POST | `/api/auth/login` | `tenant_id` | Login a portal user |
| POST | `/api/auth/refresh` | `tenant_id` | Exchange refresh token for a new access token |
| GET | `/api/auth/profile` | JWT + `tenant_id` | Get current user profile |
| PUT | `/api/auth/password` | JWT + `tenant_id` | Update current user password |
| POST | `/api/auth/logout` | JWT + `tenant_id` | Logout current user |
| GET | `/api/calendar/calendars` | `tenant_id` | List Google calendars for a tenant |
| GET | `/api/calendar/events` | `tenant_id` | List Google Calendar events |
| POST | `/api/calendar/appointments` | `tenant_id` | Create an appointment |
| GET | `/api/calendar/availability/suggestions` | `tenant_id` | List suggested available slots |
| GET | `/api/calendar/availability/next` | `tenant_id` | Get next available slot |
| GET | `/api/calendar/availability/date` | `tenant_id` | Get availability for one date |
| GET | `/api/calendar/availability/check` | `tenant_id` | Check one exact slot |
| GET | `/api/portal/dashboard/metrics` | JWT + `tenant_id` | Get dashboard metrics |
| GET | `/api/portal/dashboard/metrics/conversations` | JWT + `tenant_id` | Get daily conversation metrics |
| GET | `/api/portal/dashboard/activity` | JWT + `tenant_id` | Get recent activity |
| GET | `/api/portal/dashboard/channels` | JWT + `tenant_id` | Get channel distribution |
| GET | `/api/portal/configuration` | JWT + `tenant_id` | Get tenant configuration |
| PUT | `/api/portal/configuration` | JWT + `tenant_id` | Update tenant configuration |
| PUT | `/api/portal/configuration/business-hours` | JWT + `tenant_id` | Update business hours only |
| GET | `/api/portal/knowledge-base` | JWT + `tenant_id` | List knowledge base entries |
| GET | `/api/portal/knowledge-base/search` | JWT + `tenant_id` | Search knowledge base |
| POST | `/api/portal/knowledge-base` | JWT + `tenant_id` | Create knowledge entry |
| PUT | `/api/portal/knowledge-base/:entryId` | JWT + `tenant_id` | Update knowledge entry |
| DELETE | `/api/portal/knowledge-base/:entryId` | JWT + `tenant_id` | Delete knowledge entry |
| POST | `/api/portal/knowledge-base/bulk-update` | JWT + `tenant_id` | Replace all knowledge entries |
| GET | `/api/portal/leads` | JWT + `tenant_id` | List leads with filters |
| GET | `/api/portal/leads/stats` | JWT + `tenant_id` | Get lead stats |
| GET | `/api/portal/leads/:id` | JWT + `tenant_id` | Get lead by id |
| PATCH | `/api/portal/leads/:id/status` | JWT + `tenant_id` | Update lead status |
| GET | `/api/messenger/availability/suggestions` | JWT + `tenant_id` | Availability suggestions for AI |
| GET | `/api/messenger/availability/next` | JWT + `tenant_id` | Next available slot for AI |
| GET | `/api/messenger/availability/date/:date` | JWT + `tenant_id` | Slots for one date for AI |

---

## System and admin endpoints

### GET `/token/:tenantId`

Generates a client JWT token using the tenant id from the path.

- Auth: none
- Path params:
  - `tenantId`: tenant id
- Success response:

```json
{
  "token": "CLIENT_JWT"
}
```

- Example:

```bash
curl "http://localhost:3000/token/tenant1"
```

Note: this token belongs to the older client auth flow. No currently mounted route uses `authMiddleware`, so this token is not required by the active API surface documented below.

### GET `/admin/auth/google/:tenantId`

Starts the one-time Google OAuth flow for a tenant.

- Auth: none
- Path params:
  - `tenantId`: tenant id
- Behavior:
  - redirects the browser to Google OAuth consent screen
- Example:

```bash
curl -i "http://localhost:3000/admin/auth/google/tenant1"
```

Recommended usage: open this URL in a browser, not with a backend client.

### GET `/admin/auth/callback`

Google OAuth callback endpoint used after consent.

- Auth: none
- Query params:
  - `code`: authorization code from Google
  - `state`: tenant id
- Behavior:
  - saves tokens for the tenant
  - returns an HTML success page
  - returns an HTML error page if `refresh_token` is missing
- Example callback shape:

```text
/admin/auth/callback?code=GOOGLE_CODE&state=tenant1
```

### GET `/admin/auth/status/:tenantId`

Checks whether Google tokens are already saved for a tenant.

- Auth: none
- Path params:
  - `tenantId`: tenant id
- Success response:

```json
{
  "isConfigured": true,
  "hasRefreshToken": true,
  "setupUrl": null,
  "lastUpdated": "2026-03-19T00:00:00.000Z"
}
```

- Example:

```bash
curl "http://localhost:3000/admin/auth/status/tenant1"
```

### POST `/admin/auth/refresh/:tenantId`

Refreshes the saved Google access token using the stored refresh token.

- Auth: none
- Path params:
  - `tenantId`: tenant id
- Success response:

```json
{
  "message": "Tokens refreshed successfully"
}
```

- Common error response:

```json
{
  "error": "No refresh token available. Re-authentication required.",
  "setupUrl": "/admin/auth/google/tenant1"
}
```

- Example:

```bash
curl -X POST "http://localhost:3000/admin/auth/refresh/tenant1"
```

---

## Auth module

Common notes:

- `POST /api/auth/register` and `POST /api/auth/login` run behind `tenantMiddleware`.
- That means the tenant must already be configured and have saved Google tokens.
- The controller overwrites `tenantId` with the `tenant_id` header value. Do not rely on `tenantId` in the request body.

### POST `/api/auth/register`

Creates a new user for the tenant.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Body:
  - `email` string, required
  - `password` string, required, minimum 6 chars
  - `name` string, required
  - `role` string, optional, `admin` or `user`, default `user`
- Success response: `201`

```json
{
  "success": true,
  "data": {
    "token": "ACCESS_TOKEN",
    "refreshToken": "REFRESH_TOKEN",
    "user": {
      "_id": "....",
      "tenantId": "tenant1",
      "email": "admin@tenant1.com",
      "role": "admin",
      "name": "Admin",
      "isActive": true
    },
    "tenant": {
      "tenantId": "tenant1",
      "timezone": "America/Mexico_City"
    }
  },
  "message": "..."
}
```

- Example:

```bash
curl -X POST "http://localhost:3000/api/auth/register" \
  -H "Content-Type: application/json" \
  -H "tenant_id: tenant1" \
  -d '{
    "email": "admin@tenant1.com",
    "password": "admin123",
    "name": "Admin Tenant 1",
    "role": "admin"
  }'
```

### POST `/api/auth/login`

Authenticates a user and returns JWT tokens.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Body:
  - `email` string, required
  - `password` string, required
- Success response: `200`

```json
{
  "success": true,
  "data": {
    "token": "ACCESS_TOKEN",
    "refreshToken": "REFRESH_TOKEN",
    "user": {
      "_id": "....",
      "tenantId": "tenant1",
      "email": "admin@tenant1.com",
      "role": "admin",
      "name": "Admin Tenant 1",
      "isActive": true
    },
    "tenant": {
      "tenantId": "tenant1",
      "timezone": "America/Mexico_City"
    }
  },
  "message": "..."
}
```

- Example:

```bash
curl -X POST "http://localhost:3000/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "tenant_id: tenant1" \
  -d '{
    "email": "admin@tenant1.com",
    "password": "admin123"
  }'
```

### POST `/api/auth/refresh`

Exchanges a refresh token for a new access token.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Body:
  - `refreshToken` string, required
- Success response:

```json
{
  "success": true,
  "data": {
    "accessToken": "NEW_ACCESS_TOKEN"
  },
  "message": "..."
}
```

- Example:

```bash
curl -X POST "http://localhost:3000/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -H "tenant_id: tenant1" \
  -d '{
    "refreshToken": "REFRESH_TOKEN"
  }'
```

### GET `/api/auth/profile`

Returns the authenticated user profile.

- Auth: JWT + `tenant_id`
- Headers:
  - `Authorization: Bearer ACCESS_TOKEN`
  - `tenant_id: tenant1`
- Success response:

```json
{
  "success": true,
  "data": {
    "_id": "....",
    "tenantId": "tenant1",
    "email": "admin@tenant1.com",
    "role": "admin",
    "name": "Admin Tenant 1",
    "isActive": true,
    "createdAt": "2026-03-19T00:00:00.000Z",
    "updatedAt": "2026-03-19T00:00:00.000Z",
    "lastLogin": "2026-03-19T00:00:00.000Z"
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/auth/profile" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### PUT `/api/auth/password`

Changes the password of the authenticated user.

- Auth: JWT + `tenant_id`
- Headers:
  - `Authorization: Bearer ACCESS_TOKEN`
  - `tenant_id: tenant1`
- Body:
  - `currentPassword` string, required
  - `newPassword` string, required, minimum 6 chars
- Success response:

```json
{
  "success": true,
  "message": "..."
}
```

- Example:

```bash
curl -X PUT "http://localhost:3000/api/auth/password" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1" \
  -d '{
    "currentPassword": "admin123",
    "newPassword": "newSecurePass123"
  }'
```

### POST `/api/auth/logout`

Returns a success response. Current implementation does not blacklist or revoke tokens.

- Auth: JWT + `tenant_id`
- Headers:
  - `Authorization: Bearer ACCESS_TOKEN`
  - `tenant_id: tenant1`
- Success response:

```json
{
  "success": true,
  "message": "..."
}
```

- Example:

```bash
curl -X POST "http://localhost:3000/api/auth/logout" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

---

## Calendar module

Common notes:

- These routes are not protected with user JWT.
- They do require `tenant_id` and a tenant already configured through Google OAuth.

### GET `/api/calendar/calendars`

Lists Google calendars available for the tenant.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Success response:

```json
{
  "success": true,
  "data": [
    {
      "id": "primary",
      "summary": "Primary calendar"
    }
  ],
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/calendar/calendars" \
  -H "tenant_id: tenant1"
```

### GET `/api/calendar/events`

Lists Google Calendar events for a date range.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Query params:
  - `calendar` string, optional, default `primary`
  - `start` ISO datetime, optional, default start of current week
  - `end` ISO datetime, optional, default end of current week
- Success response:

```json
{
  "success": true,
  "data": [
    {
      "id": "google_event_id",
      "summary": "Appointment",
      "start": {
        "dateTime": "2026-03-20T09:00:00-06:00"
      },
      "end": {
        "dateTime": "2026-03-20T10:00:00-06:00"
      }
    }
  ],
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/calendar/events?calendar=primary&start=2026-03-20T00:00:00.000Z&end=2026-03-27T00:00:00.000Z" \
  -H "tenant_id: tenant1"
```

### POST `/api/calendar/appointments`

Creates an appointment in Google Calendar and stores it locally.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Body:
  - `title` string, required
  - `startTime` ISO datetime, required
  - `description` string, optional
  - `duration` number in minutes, optional, default `60`
  - `guestEmails` string array, optional
- Success response: `201`

```json
{
  "success": true,
  "data": {
    "appointmentId": "mongo_id",
    "googleEventId": "google_event_id"
  },
  "message": "..."
}
```

- Example:

```bash
curl -X POST "http://localhost:3000/api/calendar/appointments" \
  -H "Content-Type: application/json" \
  -H "tenant_id: tenant1" \
  -d '{
    "title": "Consulta inicial",
    "description": "Primera visita",
    "startTime": "2026-03-20T16:00:00.000Z",
    "duration": 60,
    "guestEmails": ["cliente@example.com"]
  }'
```

Important runtime behavior:

- One appointment per IP per day is enforced.
- If the same IP already created an appointment that day, the endpoint returns `409`.
- If the tenant is not configured, the endpoint returns `400`.
- If the requested slot is unavailable, the current implementation returns `400` and places the slot suggestions serialized inside the `error` field string.

---

## Calendar availability module

All routes below:

- use `tenant_id`
- use `tenantMiddleware`
- sync Google Calendar before calculating availability

### GET `/api/calendar/availability/suggestions`

Returns suggested available slots grouped by day.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Query params:
  - `daysAhead` number, optional, default `7`, allowed `1..90`
  - `maxSlots` number, optional, default `10`, allowed `1..100`
  - `preferredDate` ISO date or datetime, optional
  - `startDate` ISO date or datetime, optional
  - `endDate` ISO date or datetime, optional
- Rule:
  - if `startDate` is sent, `endDate` is also required
  - if `endDate` is sent, `startDate` is also required
- Success response:

```json
{
  "success": true,
  "data": {
    "tenantId": "tenant1",
    "timezone": "America/Mexico_City",
    "businessName": "Mi negocio",
    "appointmentDuration": 60,
    "days": [
      {
        "date": "2026-03-20",
        "dayOfWeek": "Viernes",
        "businessHours": {
          "start": "09:00",
          "end": "17:00"
        },
        "isBusinessDay": true,
        "slots": [
          {
            "startTime": "09:00",
            "endTime": "10:00",
            "startDateTime": "2026-03-20T09:00:00-06:00",
            "endDateTime": "2026-03-20T10:00:00-06:00",
            "duration": 60
          }
        ],
        "totalSlots": 1
      }
    ],
    "totalSlotsAvailable": 10,
    "dateRange": {
      "from": "2026-03-20",
      "to": "2026-03-27"
    }
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/calendar/availability/suggestions?daysAhead=7&maxSlots=10" \
  -H "tenant_id: tenant1"
```

### GET `/api/calendar/availability/next`

Returns the next available slot.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Query params:
  - `fromDate` ISO date or datetime, optional
  - `maxDaysAhead` number, optional, default `30`, allowed `1..90`
- Success response:

```json
{
  "success": true,
  "data": {
    "tenantId": "tenant1",
    "timezone": "America/Mexico_City",
    "businessName": "Mi negocio",
    "nextSlot": {
      "date": "2026-03-20",
      "dayOfWeek": "Viernes",
      "slot": {
        "startTime": "09:00",
        "endTime": "10:00",
        "startDateTime": "2026-03-20T09:00:00-06:00",
        "endDateTime": "2026-03-20T10:00:00-06:00",
        "duration": 60
      }
    },
    "fromDate": "2026-03-20",
    "daysSearched": 1
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/calendar/availability/next?fromDate=2026-03-20" \
  -H "tenant_id: tenant1"
```

### GET `/api/calendar/availability/date`

Returns all available slots for one specific date.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Query params:
  - `date` string, required, `YYYY-MM-DD` or ISO datetime
- Success response:

```json
{
  "success": true,
  "data": {
    "tenantId": "tenant1",
    "timezone": "America/Mexico_City",
    "businessName": "Mi negocio",
    "date": "2026-03-20",
    "dayOfWeek": "Viernes",
    "businessHours": {
      "start": "09:00",
      "end": "17:00"
    },
    "isBusinessDay": true,
    "slots": [
      {
        "startTime": "09:00",
        "endTime": "10:00",
        "startDateTime": "2026-03-20T09:00:00-06:00",
        "endDateTime": "2026-03-20T10:00:00-06:00",
        "duration": 60
      }
    ],
    "totalSlots": 8
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/calendar/availability/date?date=2026-03-20" \
  -H "tenant_id: tenant1"
```

### GET `/api/calendar/availability/check`

Checks whether one exact slot is available.

- Auth: `tenant_id`
- Headers:
  - `tenant_id: tenant1`
- Query params:
  - `startDateTime` ISO datetime, required
  - `duration` number in minutes, optional
- Success response:

```json
{
  "success": true,
  "data": {
    "available": true,
    "startDateTime": "2026-03-20T09:00:00-06:00",
    "duration": 60
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/calendar/availability/check?startDateTime=2026-03-20T09:00:00-06:00&duration=60" \
  -H "tenant_id: tenant1"
```

---

## Portal dashboard endpoints

All routes below require:

- `Authorization: Bearer ACCESS_TOKEN`
- `tenant_id: tenant1`

### GET `/api/portal/dashboard/metrics`

Returns top-level dashboard metrics.

- Query params:
  - `startDate` ISO date or datetime, optional
  - `endDate` ISO date or datetime, optional
- Success response:

```json
{
  "success": true,
  "data": {
    "conversationsDaily": 5,
    "conversationsMonthly": 120,
    "leadsMonthly": 30,
    "appointmentsMonthly": 12,
    "tokensUsed": 15432,
    "channelDistribution": {
      "webChat": 80,
      "whatsapp": 30,
      "telegram": 10
    },
    "recentActivity": []
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/dashboard/metrics?startDate=2026-03-01&endDate=2026-03-31" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### GET `/api/portal/dashboard/metrics/conversations`

Returns daily conversation aggregates.

- Query params:
  - `startDate` ISO date or datetime, optional
  - `endDate` ISO date or datetime, optional
- Success response:

```json
{
  "success": true,
  "data": [
    {
      "_id": "2026-03-19",
      "conversations": 14,
      "totalMessages": 87
    }
  ],
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/dashboard/metrics/conversations?startDate=2026-03-01&endDate=2026-03-31" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### GET `/api/portal/dashboard/activity`

Returns recent activity records.

- Query params:
  - `limit` number, optional, default `10`
- Success response:

```json
{
  "success": true,
  "data": [
    {
      "_id": "....",
      "type": "lead",
      "title": "Nuevo lead: Juan Perez",
      "description": "Lead generado con nivel de interes: high",
      "timestamp": "2026-03-19T00:00:00.000Z",
      "metadata": {}
    }
  ],
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/dashboard/activity?limit=5" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### GET `/api/portal/dashboard/channels`

Returns the distribution of conversations by channel.

- Query params:
  - `startDate` ISO date or datetime, optional
  - `endDate` ISO date or datetime, optional
- Success response:

```json
{
  "success": true,
  "data": {
    "webChat": 80,
    "whatsapp": 30,
    "telegram": 10
  },
  "message": "Distribucion por canal obtenida exitosamente"
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/dashboard/channels?startDate=2026-03-01&endDate=2026-03-31" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

---

## Portal configuration endpoints

All routes below require:

- `Authorization: Bearer ACCESS_TOKEN`
- `tenant_id: tenant1`

### GET `/api/portal/configuration`

Returns the tenant configuration. If no configuration exists yet, the service creates a default one.

- Success response:

```json
{
  "success": true,
  "data": {
    "_id": "....",
    "tenantId": "tenant1",
    "businessName": "Negocio tenant1",
    "description": "Descripcion de mi negocio",
    "phone": "",
    "email": "",
    "businessHours": {
      "monday": { "start": "09:00", "end": "17:00" },
      "tuesday": { "start": "09:00", "end": "17:00" },
      "wednesday": { "start": "09:00", "end": "17:00" },
      "thursday": { "start": "09:00", "end": "17:00" },
      "friday": { "start": "09:00", "end": "17:00" },
      "saturday": null,
      "sunday": null
    },
    "appointmentDuration": 60,
    "timezone": "America/Mexico_City",
    "language": "es"
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/configuration" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### PUT `/api/portal/configuration`

Updates one or more configuration fields.

- Body: any subset of
  - `businessName`
  - `description`
  - `phone`
  - `email`
  - `businessHours`
  - `appointmentDuration`
  - `timezone`
  - `language`
- Success response:

```json
{
  "success": true,
  "data": {
    "tenantId": "tenant1",
    "businessName": "Mi negocio",
    "appointmentDuration": 45,
    "timezone": "America/Mexico_City",
    "language": "es"
  },
  "message": "..."
}
```

- Example:

```bash
curl -X PUT "http://localhost:3000/api/portal/configuration" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1" \
  -d '{
    "businessName": "Clinica Demo",
    "description": "Consultas y seguimiento",
    "phone": "+52-555-123-4567",
    "email": "info@demo.com",
    "appointmentDuration": 45,
    "timezone": "America/Mexico_City",
    "language": "es"
  }'
```

### PUT `/api/portal/configuration/business-hours`

Updates only the `businessHours` block.

- Body:
  - `businessHours` object, required
- Success response:

```json
{
  "success": true,
  "data": {
    "tenantId": "tenant1",
    "businessHours": {
      "monday": { "start": "08:00", "end": "18:00" },
      "tuesday": { "start": "08:00", "end": "18:00" },
      "wednesday": { "start": "08:00", "end": "18:00" },
      "thursday": { "start": "08:00", "end": "18:00" },
      "friday": { "start": "08:00", "end": "18:00" },
      "saturday": { "start": "09:00", "end": "14:00" },
      "sunday": null
    }
  },
  "message": "..."
}
```

- Example:

```bash
curl -X PUT "http://localhost:3000/api/portal/configuration/business-hours" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1" \
  -d '{
    "businessHours": {
      "monday": { "start": "08:00", "end": "18:00" },
      "tuesday": { "start": "08:00", "end": "18:00" },
      "wednesday": { "start": "08:00", "end": "18:00" },
      "thursday": { "start": "08:00", "end": "18:00" },
      "friday": { "start": "08:00", "end": "18:00" },
      "saturday": { "start": "09:00", "end": "14:00" },
      "sunday": null
    }
  }'
```

Recommended sequence: call `GET /api/portal/configuration` at least once before `PUT /business-hours`, because the service expects an existing configuration document for this endpoint.

---

## Portal knowledge base endpoints

All routes below require:

- `Authorization: Bearer ACCESS_TOKEN`
- `tenant_id: tenant1`

### GET `/api/portal/knowledge-base`

Returns knowledge base entries for the tenant.

- Query params:
  - `category` string, optional
- Success response:

```json
{
  "success": true,
  "data": [
    {
      "_id": "....",
      "tenantId": "tenant1",
      "text": "Nuestros horarios son de lunes a viernes...",
      "createdAt": "2026-03-19T00:00:00.000Z",
      "updatedAt": "2026-03-19T00:00:00.000Z"
    }
  ],
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/knowledge-base?category=horarios" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### GET `/api/portal/knowledge-base/search`

Searches the knowledge base by text.

- Query params:
  - `query` string, required
  - `limit` number, optional, default `10`
- Success response:

```json
{
  "success": true,
  "data": [
    {
      "_id": "....",
      "tenantId": "tenant1",
      "text": "Nuestros horarios son de lunes a viernes...",
      "category": "horarios",
      "tags": ["horarios"],
      "createdAt": "2026-03-19T00:00:00.000Z",
      "updatedAt": "2026-03-19T00:00:00.000Z"
    }
  ],
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/knowledge-base/search?query=horarios&limit=5" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

Important: the correct query parameter is `query`, not `q`.

### POST `/api/portal/knowledge-base`

Creates one knowledge base entry.

- Body:
  - `text` string, required
  - any extra fields are accepted by the controller but the create service currently persists only `text`, `tenantId`, `createdAt`, and `updatedAt`
- Success response: `201`

```json
{
  "success": true,
  "data": {
    "_id": "....",
    "tenantId": "tenant1",
    "text": "Aceptamos pagos con tarjeta",
    "createdAt": "2026-03-19T00:00:00.000Z",
    "updatedAt": "2026-03-19T00:00:00.000Z"
  },
  "message": "..."
}
```

- Example:

```bash
curl -X POST "http://localhost:3000/api/portal/knowledge-base" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1" \
  -d '{
    "text": "Aceptamos pagos con tarjeta, transferencia y efectivo"
  }'
```

### PUT `/api/portal/knowledge-base/:entryId`

Updates an existing knowledge entry.

- Path params:
  - `entryId` required
- Body:
  - any non-empty JSON object
  - most commonly `text`
- Success response:

```json
{
  "success": true,
  "data": {
    "_id": "....",
    "tenantId": "tenant1",
    "text": "Texto actualizado",
    "createdAt": "2026-03-19T00:00:00.000Z",
    "updatedAt": "2026-03-19T01:00:00.000Z"
  },
  "message": "..."
}
```

- Example:

```bash
curl -X PUT "http://localhost:3000/api/portal/knowledge-base/ENTRY_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1" \
  -d '{
    "text": "Nuevo texto de la entrada"
  }'
```

### DELETE `/api/portal/knowledge-base/:entryId`

Deletes one knowledge entry.

- Path params:
  - `entryId` required
- Success response:

```json
{
  "success": true,
  "message": "..."
}
```

- Example:

```bash
curl -X DELETE "http://localhost:3000/api/portal/knowledge-base/ENTRY_ID" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### POST `/api/portal/knowledge-base/bulk-update`

Deletes all current tenant entries and recreates them from the provided list.

- Body:
  - `entries` array, required
- Success response:

```json
{
  "success": true,
  "data": {
    "success": 3,
    "failed": 0
  },
  "message": "..."
}
```

- Example:

```bash
curl -X POST "http://localhost:3000/api/portal/knowledge-base/bulk-update" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1" \
  -d '{
    "entries": [
      { "text": "Horario: lunes a viernes de 9 a 17" },
      { "text": "Consultas con cita previa" },
      { "text": "Aceptamos pagos en efectivo y tarjeta" }
    ]
  }'
```

Important runtime behavior:

- This endpoint is destructive for the tenant knowledge base because it first runs `deleteMany`.
- During creation, the service currently persists only `text` plus tenant/timestamps. If you send `category` or `tags`, they are ignored during the insert step.

---

## Portal leads endpoints

All routes below require:

- `Authorization: Bearer ACCESS_TOKEN`
- `tenant_id: tenant1`

### GET `/api/portal/leads`

Returns paginated leads with filters.

- Query params:
  - `status` string, optional
  - `intent_level` string, optional
  - `channel` string, optional, one of `web`, `whatsapp`, `telegram`
  - `search` string, optional
  - `startDate` ISO date or datetime, optional
  - `endDate` ISO date or datetime, optional
  - `limit` number, optional, default `20`
  - `page` number, optional, default `1`
  - `sortBy` string, optional, one of `created_at`, `updated_at`, `name`, `email`
  - `sortOrder` string, optional, `asc` or `desc`, default `desc`
- Success response:

```json
{
  "success": true,
  "data": {
    "leads": [
      {
        "_id": "....",
        "tenantId": "tenant1",
        "name": "Juan Perez",
        "email": "juan@example.com",
        "action": "contact",
        "response": "Quiero una cita",
        "status": "new",
        "intent_level": "high",
        "channel": "web",
        "created_at": "2026-03-19T00:00:00.000Z",
        "updated_at": "2026-03-19T00:00:00.000Z"
      }
    ],
    "total": 42,
    "page": 1,
    "totalPages": 3,
    "limit": 20
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/leads?status=new&intent_level=high&channel=web&limit=10&page=1&sortBy=created_at&sortOrder=desc" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### GET `/api/portal/leads/stats`

Returns aggregate stats for leads.

- Query params:
  - `startDate` ISO date or datetime, optional
  - `endDate` ISO date or datetime, optional
- Success response:

```json
{
  "success": true,
  "data": {
    "total": 42,
    "byStatus": {
      "new": 20,
      "contacted": 10
    },
    "byIntentLevel": {
      "high": 15,
      "medium": 17,
      "low": 10
    },
    "byChannel": {
      "web": 25,
      "whatsapp": 12,
      "telegram": 5
    }
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/leads/stats?startDate=2026-03-01&endDate=2026-03-31" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### GET `/api/portal/leads/:id`

Returns one lead by Mongo id.

- Path params:
  - `id` required
- Success response:

```json
{
  "success": true,
  "data": {
    "_id": "....",
    "tenantId": "tenant1",
    "name": "Juan Perez",
    "email": "juan@example.com",
    "action": "contact",
    "response": "Quiero una cita",
    "status": "new",
    "intent_level": "high",
    "channel": "web"
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/portal/leads/LEAD_ID" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### PATCH `/api/portal/leads/:id/status`

Updates only the lead status.

- Path params:
  - `id` required
- Body:
  - `status` string, required
- Success response:

```json
{
  "success": true,
  "data": {
    "_id": "....",
    "tenantId": "tenant1",
    "status": "contacted",
    "updated_at": "2026-03-19T01:00:00.000Z"
  },
  "message": "..."
}
```

- Example:

```bash
curl -X PATCH "http://localhost:3000/api/portal/leads/LEAD_ID/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1" \
  -d '{
    "status": "contacted"
  }'
```

---

## Messenger availability endpoints

All routes below require:

- `Authorization: Bearer ACCESS_TOKEN`
- `tenant_id: tenant1`

These endpoints are designed for AI or chat integrations that need availability data in a simpler shape than `/api/calendar/availability/*`.

### GET `/api/messenger/availability/suggestions`

Returns a flat list of suggested available slots.

- Query params:
  - `daysAhead` number, optional, default `7`
  - `maxSlots` number, optional, default `10`
  - `preferredDate` ISO date or datetime, optional
- Success response:

```json
{
  "success": true,
  "data": {
    "tenantId": "tenant1",
    "timezone": "America/Mexico_City",
    "businessName": "Mi negocio",
    "appointmentDuration": 60,
    "suggestedSlots": [
      {
        "date": "2026-03-20",
        "dayOfWeek": "Viernes",
        "startTime": "09:00",
        "endTime": "10:00",
        "startDateTime": "2026-03-20T09:00:00-06:00",
        "endDateTime": "2026-03-20T10:00:00-06:00",
        "duration": 60
      }
    ],
    "totalSlotsAvailable": 1,
    "dateRange": {
      "from": "2026-03-20",
      "to": "2026-03-27"
    }
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/messenger/availability/suggestions?daysAhead=7&maxSlots=5" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### GET `/api/messenger/availability/next`

Returns only the next available slot.

- Query params:
  - `fromDate` ISO date or datetime, optional
- Success response:

```json
{
  "success": true,
  "data": {
    "nextAvailableSlot": {
      "date": "2026-03-20",
      "dayOfWeek": "Viernes",
      "startTime": "09:00",
      "endTime": "10:00",
      "startDateTime": "2026-03-20T09:00:00-06:00",
      "endDateTime": "2026-03-20T10:00:00-06:00",
      "duration": 60
    }
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/messenger/availability/next?fromDate=2026-03-20" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

### GET `/api/messenger/availability/date/:date`

Returns all available slots for one date.

- Path params:
  - `date` required, `YYYY-MM-DD`
- Success response:

```json
{
  "success": true,
  "data": {
    "date": "2026-03-20",
    "availableSlots": [
      {
        "date": "2026-03-20",
        "dayOfWeek": "Viernes",
        "startTime": "09:00",
        "endTime": "10:00",
        "startDateTime": "2026-03-20T09:00:00-06:00",
        "endDateTime": "2026-03-20T10:00:00-06:00",
        "duration": 60
      }
    ],
    "totalSlots": 1
  },
  "message": "..."
}
```

- Example:

```bash
curl "http://localhost:3000/api/messenger/availability/date/2026-03-20" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "tenant_id: tenant1"
```

---

## Recommended usage flow

If you are integrating this API from scratch, the safest order is:

1. Configure Google for the tenant with `GET /admin/auth/google/:tenantId`
2. Verify setup with `GET /admin/auth/status/:tenantId`
3. Register or login a portal user with `/api/auth/register` or `/api/auth/login`
4. Use the returned access token on protected portal and messenger routes
5. Read and update tenant configuration from `/api/portal/configuration`
6. Query availability with `/api/calendar/availability/*` or `/api/messenger/availability/*`
7. Create appointments with `POST /api/calendar/appointments`

## Notes about current implementation

- The active API exposes 38 endpoints.
- Some test/example files in the repo use outdated request shapes. This document follows the mounted source code, not the old test scripts.
- `POST /api/auth/register` and `POST /api/auth/login` require `tenant_id` and also depend on `tenantMiddleware`, so Google tenant setup is effectively a prerequisite.
- The knowledge base create and bulk insert flows currently persist only `text` plus tenant/timestamps.
- `POST /api/calendar/appointments` enforces one appointment per IP per day.
