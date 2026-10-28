# Parcelly: Courier Tracking System on Neo4j (DA3, BACSE202)

A courier tracking website on **Neo4j Aura Free**: FastAPI backend, plain HTML / CSS / vanilla JavaScript frontend (dark theme). The repo also keeps the original Cypher scripts and the command line app.

| Path | Purpose |
| --- | --- |
| `01_constraints.cypher` ... `05_access_control_demo.cypher` | Schema, data, CRUD, graph queries G1-G16, access-control design |
| `backend/` | FastAPI app: `routers/` (HTTP), `services/` (all Cypher), `schemas.py`, `auth.py`, `security.py`, `pages.py` |
| `static/` | `pages/` (HTML), `js/` (shared `ui.js`, `layout.js`, `pages/*.js`), `css/theme.css`, `img/`, `vendor/` (local vis-network and fonts) |
| `tests/` | pytest (unit + Aura), `tests/e2e` (Playwright) |
| `docs/page_to_query_map.md` | every page, tab and button to endpoint to Cypher |
| `Dockerfile`, `docker-compose.yml`, `Caddyfile` | production image behind Caddy with automatic HTTPS |
| `app/` | original CLI (`courier_app.py`), still works |

## Pages

| URL | Who | What |
| --- | --- | --- |
| `/login` | public | email-only demo login |
| `/` | logged in | staff: **Overview** (KPIs, needs attention, recent activity, hub map). customer: **Home** (search, parcels in progress) |
| `/shipments` | logged in | staff: all; customer: own. Search, status chips, sort, paging |
| `/shipments/new` | logged in | 3-step booking (parties, packages, review and pay) |
| `/shipments/{id}` | owner or staff | Journey, Details, Graph; staff actions (add event, record payment, print label) |
| `/network` | staff | one map; tabs **Routes** (fewest hops / km) and **Hub impact** |
| `/customers`, `/customers/{id}` | staff | list, add / edit (modal), delete (confirm) |
| `/reports`, `/reports/{slug}` | staff | grouped reports, chart, CSV, print, "Show query" with the G-code |
| `/account` | logged in | profile; customers edit phone and address |

Old `.html` URLs 301-redirect to these. Unknown pages show a branded 404; a customer opening a staff page or someone else's shipment sees a branded 403 page.

## Run locally (macOS)

```bash
cd Courier-Management-System
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp app/.env.example app/.env        # first time: fill in your Aura details and APP_SECRET
make dev                            # or: uvicorn backend.main:app --reload
```
Open http://127.0.0.1:8000 (API docs at `/docs` in development). The database must already be loaded (`python app/load_data.py 01_constraints.cypher 02_load_data.cypher`); the web app never loads, wipes or reseeds data.

### Environment variables (names only; values in `app/.env`, never committed)

| Name | Purpose |
| --- | --- |
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` | Aura connection |
| `APP_SECRET` | signs the session cookie (32+ characters; required, the app refuses to start without it) |
| `APP_ENV` | `development` (default) or `production` (Secure cookies, HSTS, `/docs` hidden, no demo login chips) |
| `ENABLE_DOCS` | `true` to expose `/docs`, `/redoc`, `/openapi.json` in production |
| `ALLOWED_ORIGINS` | comma separated origins allowed for CORS and the CSRF check |
| `LOG_LEVEL` | `INFO` (default) |
| `SITE_ADDRESS` | hostname for Caddy (compose only), for example `85-211-182-145.sslip.io` |

### Demo logins (email only, no password)

STAFF: `divya@courier.com`, `naveen@courier.com`, `karthik@courier.com`. CUSTOMER: `arun@example.com`, `priya@example.com`, `rahul@example.com`, `meera@example.com`.

## Tests

```bash
make test     # pytest: unit tests + Aura tests (Aura tests skip when credentials are absent)
make e2e      # Playwright smoke test: staff books, delivers and pays; customer scope and 403 pages
make lint     # ruff
make audit    # pip-audit on the pinned runtime dependencies
```
Tests that write use customers 9001 / 9002 and what they send, delete it all afterwards and assert the baseline counts (Branch 6, Customer 4, Employee 3, Package 7, Payment 5, Shipment 5, TrackingEvent 12). For the e2e test run `playwright install chromium` once.

## Business rules (enforced in the service layer; Aura Free has no NOT NULL / CHECK / triggers)

* **Status order** (`backend/services/status.py`, server-side; the UI only offers valid options): BOOKED to PICKED_UP; PICKED_UP to IN_TRANSIT; IN_TRANSIT to AT_BRANCH or OUT_FOR_DELIVERY; AT_BRANCH to IN_TRANSIT or OUT_FOR_DELIVERY; OUT_FOR_DELIVERY to DELIVERED. DELAYED is allowed from any non-final status and then rejoins the chain it interrupted. CANCELLED only while BOOKED. DELIVERED and CANCELLED are final. A bad move returns 409 `INVALID_TRANSITION` with the allowed statuses.
* **Delivery place**: DELIVERED must be recorded at a branch or hub in the receiver's city when one exists (assumption: matched by `Branch.city` = `Customer.city`); if the city has no branch, any location is accepted.
* **Payments**: one payment per shipment; the amount cannot exceed the outstanding balance; only `PAID` payments count as paid. `paymentState` is PAID, PARTIAL or UNPAID.
* **Ids** are `max(id)+1` computed inside the write transaction; a race hits the unique constraint (customers retry, others return 409).
* Validation (required fields, positive weights and amounts, whitelists) is in `backend/schemas.py`. Uniqueness comes from the database constraints; `ConstraintError` becomes 409.
* Booking also writes the first `BOOKED` tracking event. Staff may record the payment at booking.
* **Rate card** (demo, `RATE_CARD` in `backend/config.py`; used when no amount is given and for the price preview): price = base + per kg x total weight.

  | Type | Base | Per kg |
  | --- | --- | --- |
  | Standard | ₹100 | ₹20 |
  | Express | ₹120 | ₹40 |
  | Overnight | ₹150 | ₹60 |

* Customer lookup by email (for choosing a receiver) returns only `{exists, displayName}` to customers ("Priya S."); staff also get id, name and city. Rate limited (30 per minute per session, 60 per IP).

## Security

* Cookie: `HttpOnly`, `SameSite=Lax`, `Secure` in production, 8 hour expiry, signed with `APP_SECRET`.
* **CSRF**: every POST / PATCH / DELETE must carry an `Origin` (or `Referer`) whose host equals the request host or is in `ALLOWED_ORIGINS`; in production a request with neither header is rejected. Together with SameSite=Lax this blocks cross-site requests without tokens.
* Headers on every response: `Content-Security-Policy` (everything `self`; no external scripts, styles or fonts), `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options: DENY`, `Permissions-Policy`, HSTS in production. vis-network injects a fixed set of style blocks, allowed by hash in `backend/security.py` (re-derive after upgrading it, see `static/vendor/README.md`). `/docs` uses its own relaxed policy and is off in production.
* Login is rate limited (10 per minute per IP); failures are logged without the submitted data. The limiter is in memory, so the container runs a single process.
* CORS: no wildcard; only `ALLOWED_ORIGINS`, or none.
* Errors are `{detail, code}` JSON for the API and branded pages for browsers; stack traces and connection details are never returned. One log line per request (method, path, status, duration), never bodies or cookies.
* All third-party assets are vendored under `static/vendor` (versions and licences in its README).

## Deploy on a VPS (Ubuntu, Docker, Caddy, sslip.io)

```bash
# 1. install Docker (https://docs.docker.com/engine/install/ubuntu/), open ports 80 and 443
git clone https://github.com/Asma-Zain/Courier-Management-System.git && cd Courier-Management-System
git checkout web-app                       # or main once merged
# 2. create the secrets file (never committed). Fill the NEO4J_* values and a 32+ character APP_SECRET
cp app/.env.example app/.env && nano app/.env
# 3. choose the hostname (the VPS IP with dashes + .sslip.io) and start
export SITE_ADDRESS=85-211-182-145.sslip.io
docker compose up --build -d
# 4. check
curl -s https://$SITE_ADDRESS/healthz      # {"status":"ok"}
curl -s https://$SITE_ADDRESS/readyz       # {"status":"ready"}  (needs Aura reachable)
```
The container only needs outbound access to Aura over `neo4j+s://`. Compose forces `APP_ENV=production`.

**Free Aura instances pause when idle: resume yours in the Aura console before a demo.** The first request after a pause can fail with 503 until it is running.

## Known limitations

* Login is **email only, no password** (demo; out of scope for this project).
* Aura Free: no custom roles (`05_access_control_demo.cypher` is a design, not run), no property-existence constraints, no triggers.
* The shipment list filters, sorts and pages in Python after a role-scoped Cypher query (fine for this data size).
* The route map on a shipment is drawn from scan locations; the data has no coordinates or live GPS.

## Command line app (original)

```bash
cd app && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python courier_app.py        # needs app/.env
```
