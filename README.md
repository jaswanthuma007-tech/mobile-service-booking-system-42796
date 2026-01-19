# Mobile Service Booking System

This repository contains a simple service booking backend (Flask) intended to be consumed by a React frontend.

## Backend (Flask) API

Base URL (dev): `http://localhost:5000` (preferred)

Swagger/OpenAPI UI: `http://localhost:5000/docs`

> Note: the backend port can be overridden with `PORT` (defaults to 5000).

### Health
- `GET /` → `{ "message": "Healthy" }`

### Reference data
- `GET /api/brands` → list brands
- `GET /api/models?brand=<brand_id>` → list models for a brand
- `GET /api/problems` → list problems

### Booking
- `POST /api/booking` → create booking, returns booking id
- `GET /api/booking?id=<booking_id>` → retrieve booking by id

Example create booking:
```json
{
  "customer_name": "Jane Doe",
  "phone": "+1 555-0100",
  "email": "jane@example.com",
  "brand_id": 1,
  "model_id": 1,
  "problem_id": 1,
  "notes": "Please call before arriving."
}
```

Response:
```json
{ "booking_id": 123 }
```

### Admin
- `GET /api/admin/bookings` → list bookings (supports filters)
  - optional query params: `status`, `brand_id`, `model_id`, `problem_id`, `search`, `limit`, `offset`
- `POST /api/admin/update_status` → update booking status

Update status request:
```json
{ "booking_id": 123, "status": "in_progress" }
```

Valid statuses: `new`, `in_progress`, `completed`, `cancelled`

## Configuration

The backend uses SQLite. The DB path is read from environment variable:

- `SQLITE_DB` (path to sqlite database file)

CORS is enabled for the frontend dev server at `http://localhost:3000` for `/api/*` routes.
