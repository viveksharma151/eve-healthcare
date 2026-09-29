# EVE Healthcare — Diagnostic Test Booking & Payment Backend

A backend service built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL/SQLite** for managing diagnostic centres, test catalogs, appointment bookings, simulated payments, and idempotent payment webhook handling.

---

## Architecture & Tech Stack

- **Framework**: FastAPI (Python 3.12)
- **Data Validation & Serialization**: Pydantic v2
- **ORM / Database**: SQLAlchemy 2.0 (PostgreSQL for production/Docker; SQLite for zero-setup local dev & tests)
- **Authentication**: JWT (JSON Web Tokens) with `HS256` and `bcrypt` password hashing
- **Testing**: `pytest` with an in-memory SQLite database and isolated transactions
- **Containerization**: Multi-stage `Dockerfile` and `docker-compose.yml` (PostgreSQL 16 + Redis + API)
- **API Documentation**: Interactive OpenAPI Swagger docs available at `/docs` and ReDoc at `/redoc`

---

## Project Structure

```
├── app/
│   ├── api/
│   │   ├── deps.py              # Auth & session dependencies (Bearer JWT, staff checks)
│   │   └── v1/
│   │       ├── auth.py          # Signup, Login, Profile endpoints
│   │       ├── centres.py       # Diagnostic centres & test pricing management
│   │       ├── tests.py         # Global test catalog endpoints
│   │       ├── bookings.py      # Booking scheduling & lifecycle (PENDING -> CONFIRMED/CANCELLED)
│   │       ├── payments.py      # /payments/ and /payments/webhook/ handlers
│   │       └── router.py        # Central API v1 router
│   ├── core/
│   │   ├── constants.py         # Enums (BookingStatus, PaymentStatus, WebhookStatus)
│   │   └── security.py          # Bcrypt hashing & JWT encode/decode
│   ├── models/
│   │   ├── user.py              # User model (patients & staff)
│   │   ├── diagnostic.py        # DiagnosticCentre, DiagnosticTest, CentreTest (pricing junction)
│   │   ├── booking.py           # Booking model with unique reference codes
│   │   └── payment.py           # Payment ledger & WebhookEvent (idempotency table)
│   ├── schemas/                 # Pydantic v2 schemas for requests & responses
│   ├── config.py                # Environment configuration via pydantic-settings
│   ├── database.py              # Engine setup & session dependency
│   └── main.py                  # FastAPI application entrypoint & OpenAPI specs
├── tests/
│   ├── conftest.py              # Pytest fixtures, in-memory DB, auth tokens, sample catalogue
│   ├── test_auth.py             # Auth integration tests (signup, login, bad credentials)
│   ├── test_centres_and_tests.py# Diagnostic centres, tests, search, pricing tests
│   ├── test_bookings.py         # Scheduling, validation, ownership & cancellation tests
│   └── test_payments_and_webhook.py # Simulated payment & idempotent webhook tests
├── seed.py                      # Database seeding script with realistic diagnostic data
├── requirements.txt             # Pinned Python dependencies
├── Dockerfile                   # Production container definition
├── docker-compose.yml           # PostgreSQL + Redis + API container stack
├── pytest.ini                   # Pytest configuration
└── README.md                    # Documentation & setup guide
```

---

## Quickstart

### Option 1: Local Setup (Recommended for quick evaluation)

The project defaults to an embedded SQLite database (`sqlite:///./eve_healthcare.db`) when run locally, requiring zero external database installations.

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd EVE-healthcare
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # On macOS / Linux:
   python3 -m venv venv
   source venv/bin/activate

   # On Windows (PowerShell):
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed the database** (creates sample centres, tests, prices, and test accounts):
   ```bash
   python seed.py
   ```
   *Default Accounts seeded:*
   - **Patient User**: `patient@example.com` / `password123`
   - **Staff / Admin User**: `admin@evehealthcare.com` / `admin123`

5. **Start the development server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - API is running at: `http://localhost:8000`
   - Interactive Swagger docs: `http://localhost:8000/docs`

---

### Option 2: Docker Compose (PostgreSQL + Redis + FastAPI)

If you have Docker and Docker Compose installed:

```bash
docker compose up --build
```

This starts:
- **PostgreSQL 16** on `localhost:5432`
- **Redis 7** on `localhost:6379`
- **API Server** on `http://localhost:8000` (auto-seeds database on startup)

---

## Running the Test Suite

The test suite runs against an isolated in-memory SQLite database (`sqlite:///:memory:`) using `pytest` and `fastapi.testclient.TestClient`. Every test runs within a fresh, isolated database transaction.

```bash
pytest
```

To run with verbose output:
```bash
pytest -v
```

---

## Database & Schema Design

```
  +------------------+         +---------------------+         +-------------------+
  |      users       |         |   diagnostic_tests  |         | diagnostic_centres|
  +------------------+         +---------------------+         +-------------------+
  | id (PK)          |         | id (PK)             |         | id (PK)           |
  | email (UQ)       |         | code (UQ)           |         | name              |
  | hashed_password  |         | name                |         | location          |
  | full_name        |         | description         |         | contact_phone     |
  | is_staff         |         +----------+----------+         | is_active         |
  +--------+---------+                    |                    +---------+---------+
           |                              |                              |
           |                              +--------------+---------------+
           |                                             |
           |                                   +---------v-----------+
           |                                   |    centre_tests     |
           |                                   +---------------------+
           |                                   | id (PK)             |
           |                                   | centre_id (FK)      |
           |                                   | test_id (FK)        |
           |                                   | price (Numeric)     |
           |                                   | is_available (Bool) |
           |                                   +----------+----------+
           |                                              |
           |                  +---------------------------+
           |                  |
  +--------v------------------v------+               +------------------------+
  |             bookings             |               |     webhook_events     |
  +----------------------------------+               +------------------------+
  | id (PK)                          |               | id (PK)                |
  | booking_reference (UQ, BK-XXXX)  |               | event_id (UQ, indexed) |
  | user_id (FK -> users.id)         |               | event_type             |
  | centre_id (FK -> centres.id)     |               | booking_id             |
  | test_id (FK -> tests.id)         |               | payload (JSON)         |
  | appointment_datetime (DateTime)  |               | status (PROCESSED)     |
  | amount (Numeric, authoritative)  |               +------------------------+
  | status (PENDING/CONFIRMED/etc)   |
  +----------------+-----------------+
                   | 1
                   |
                   | N
  +----------------v-----------------+
  |             payments             |
  +----------------------------------+
  | id (PK)                          |
  | payment_reference (UQ, PAY-XXXX) |
  | booking_id (FK -> bookings.id)   |
  | amount (Numeric)                 |
  | status (SUCCESS/FAILED/PENDING)  |
  | provider_transaction_id          |
  +----------------------------------+
```

### Key Relational Design Decisions:
1. **Centre-Specific Test Pricing (`centre_tests`)**: In real healthcare networks, the same diagnostic test (e.g. Complete Blood Count or MRI) has different pricing depending on lab equipment and location. Rather than coupling price directly to the test, the `centre_tests` junction table models `(centre_id, test_id) -> (price, is_available)`.
2. **Authoritative Server-Side Pricing**: When creating a booking, the client does not specify the price. The server looks up the current price for that test at that centre from `centre_tests`, preventing price tampering.
3. **Webhook Idempotency Ledger (`webhook_events`)**: Webhooks from payment gateways can be delivered multiple times due to network retries. We enforce an `event_id` unique constraint in the `webhook_events` table. If an event is received again, the system immediately returns a successful response without re-executing transactions or duplicating records.

---

## API Endpoints & Example Requests

All versioned endpoints are prefixed with `/api/v1`. To strictly conform to the prompt specifications, `/payments/` and `/payments/webhook/` are also mounted at the root path.

### 1. Authentication

#### User Signup
```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "rohan@example.com",
    "full_name": "Rohan Verma",
    "password": "securepassword123"
  }'
```

#### User Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "rohan@example.com",
    "password": "securepassword123"
  }'
```
*Returns JWT access token:*
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "rohan@example.com",
    "full_name": "Rohan Verma",
    "is_active": true,
    "is_staff": false
  }
}
```

---

### 2. Diagnostic Centres & Tests

#### List Diagnostic Centres (with location search & test availability)
```bash
# Search by location (e.g. Indiranagar)
curl -X GET "http://localhost:8000/api/v1/centres/?location=Indiranagar"

# Filter centres offering a specific test (e.g. test_id=1 for CBC)
curl -X GET "http://localhost:8000/api/v1/centres/?test_id=1"
```

#### Get Centre Details (includes test catalog and pricing)
```bash
curl -X GET http://localhost:8000/api/v1/centres/1
```

#### Add or Update Test Pricing for a Centre
```bash
curl -X POST http://localhost:8000/api/v1/centres/1/tests \
  -H "Content-Type: application/json" \
  -d '{
    "test_id": 2,
    "price": 720.00,
    "is_available": true
  }'
```

---

### 3. Bookings

#### Create a Booking (Requires Authentication)
```bash
curl -X POST http://localhost:8000/api/v1/bookings/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "centre_id": 1,
    "test_id": 1,
    "appointment_datetime": "2026-10-15T10:30:00Z",
    "notes": "Routine annual checkup"
  }'
```
*Response:*
```json
{
  "id": 1,
  "booking_reference": "BK-9A2E4F18",
  "user_id": 1,
  "centre_id": 1,
  "test_id": 1,
  "centre_name": "CareMax Diagnostic Centre - Indiranagar",
  "centre_location": "100 Feet Rd, Indiranagar, Bengaluru, Karnataka",
  "test_name": "Complete Blood Count",
  "appointment_datetime": "2026-10-15T10:30:00",
  "amount": "350.00",
  "status": "PENDING",
  "notes": "Routine annual checkup"
}
```

#### View User's Bookings
```bash
curl -X GET http://localhost:8000/api/v1/bookings/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

#### Cancel a Booking
```bash
curl -X POST http://localhost:8000/api/v1/bookings/1/cancel \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

---

### 4. Simulated Payment Service

#### Process Simulated Payment (`POST /payments/`)
Simulates payment processing. You can optionally force `simulate_status` to `"SUCCESS"` or `"FAILED"`.

```bash
curl -X POST http://localhost:8000/payments/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 1,
    "simulate_status": "SUCCESS"
  }'
```
*Response:*
```json
{
  "payment_reference": "PAY-3C7D8102",
  "booking_id": 1,
  "amount": "350.00",
  "status": "SUCCESS",
  "booking_status": "CONFIRMED",
  "provider_transaction_id": "mock_txn_9a8df102c918",
  "failure_reason": null,
  "message": "Simulated payment succeeded and booking confirmed."
}
```

---

### 5. Payment Webhook (`POST /payments/webhook/`)

#### Receive Webhook Notification
```bash
curl -X POST http://localhost:8000/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_live_1092830192",
    "event_type": "payment.succeeded",
    "booking_id": 1,
    "amount": 350.00,
    "status": "SUCCESS",
    "provider_transaction_id": "txn_mock_987654"
  }'
```
*First response:*
```json
{
  "status": "processed",
  "event_id": "evt_live_1092830192",
  "booking_id": 1,
  "booking_status": "CONFIRMED",
  "message": "Payment processed successfully and booking confirmed."
}
```

#### Verifying Idempotency
If the payment gateway re-sends the same payload with the identical `event_id`:
```bash
curl -X POST http://localhost:8000/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_live_1092830192",
    "event_type": "payment.succeeded",
    "booking_id": 1,
    "amount": 350.00,
    "status": "SUCCESS",
    "provider_transaction_id": "txn_mock_987654"
  }'
```
*Safe Idempotent response:*
```json
{
  "status": "already_processed",
  "event_id": "evt_live_1092830192",
  "booking_id": 1,
  "booking_status": "CONFIRMED",
  "message": "Event 'evt_live_1092830192' has already been processed. No duplicate mutations performed."
}
```
No secondary payment record is created, and booking state remains uncorrupted.

---

## Edge Cases Handled

| Edge Case | How It Is Handled |
| :--- | :--- |
| **Tampered Booking Price** | The booking price is never trusted from the client payload. It is resolved directly from the centre's published `centre_tests` pricing table. |
| **Past Appointment Dates** | Pydantic field validator checks that `appointment_datetime` is in the future. Past dates return `422 Unprocessable Content`. |
| **Inactive Centre / Unavailable Test** | Ensures the centre is active and the specific test is enabled at that centre. Otherwise returns `400 Bad Request`. |
| **Unauthorized Access (IDOR)** | Normal patients can only view, pay for, and cancel bookings that belong to their own `user_id`. Attempting to access another patient's booking returns `403 Forbidden`. |
| **Duplicate Webhook Delivery** | Incoming `event_id` is tracked in the `webhook_events` idempotency table. Duplicate deliveries return `200 OK` with status `already_processed` without re-executing transactions. |
| **Webhook Amount Mismatch** | Validates that the amount reported by the payment webhook matches the booking amount on record. |
| **Invalid State Transitions** | Prevents paying for already `CONFIRMED` or `CANCELLED` bookings. Prevents cancelling already `CANCELLED` or `FAILED` bookings. |
| **Invalid Booking IDs** | Missing resources cleanly return `404 Not Found`. |

---

## Important Assumptions Made

1. **Test Availability & Pricing**: Different diagnostic labs charge different amounts for the same medical test due to lab tier and operational costs. We modeled this as an explicit association table (`centre_tests`) rather than hardcoding price on the global test catalog.
2. **Payment Lifecycle**: In a typical diagnostic workflow, users book a slot (status: `PENDING`), and then complete payment either immediately online or via asynchronous gateway callback. Successful payment transitions the booking to `CONFIRMED`.
3. **Webhook Security**: Webhook endpoints in production typically verify cryptographic signatures (e.g., Stripe's `Stripe-Signature` or Razorpay HMAC-SHA256). In this simulated implementation, idempotency is enforced via `event_id` uniqueness and payload amount verification.
4. **Timezones**: Datetimes are accepted in ISO-8601 UTC format.

---

## What I Would Improve With More Time

1. **Slot Availability & Capacity Management**: Model time slots (e.g. 30-minute intervals) with maximum capacity per centre to avoid double-booking technician slots.
2. **Distributed Locking (Redis Redlock)**: Use Redis distributed locks during payment processing and booking creation to prevent race conditions during high-volume flash sales.
3. **Asynchronous Background Jobs (Celery / ARQ)**: Offload email/SMS appointment confirmations and invoice PDF generation to background workers.
4. **Database Migrations (Alembic)**: While `Base.metadata.create_all()` is convenient for initial setup, production workflows benefit from versioned Alembic migration scripts.
5. **Rate Limiting**: Implement Redis-backed token bucket rate limiting on sensitive endpoints (`/auth/login`, `/payments/`) to mitigate brute-force attacks and abuse.
