# Courier Tracking System: Neo4j (DA3)

Graph-database version of the Courier Tracking System (BACSE202), with the original Cypher scripts, a command line app and a **web app (FastAPI + plain HTML/JS) styled after the Parcelly dark UI**.

## What is in this repo
| Path | Purpose |
| --- | --- |
| 01_constraints.cypher ... 05_access_control_demo.cypher | Schema, data, CRUD, 16 graph queries, access-control design |
| app/ | Original CLI (`courier_app.py`) and `load_data.py`. Still works as a fallback |
| backend/ | FastAPI app: `routers/` (HTTP), `services/` (all Cypher), `schemas.py` (validation), `auth.py` |
| static/ | Frontend: one HTML page per feature, `css/theme.css` (all colours/fonts/spacing as CSS variables), `js/api.js` + `js/pages/*.js` |
| tests/ | pytest suite (runs against the real database, uses test ids, cleans up) |
| docs/page_to_query_map.md | Every page/button to endpoint to Cypher |

## Run the web app (macOS)
```bash
cd Courier-Management-System            # repo root
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp app/.env.example app/.env            # then fill in your Aura details (first time only)
uvicorn backend.main:app --reload
```
Open http://127.0.0.1:8000 (API docs at http://127.0.0.1:8000/docs).

The database must already be loaded (`python app/load_data.py 01_constraints.cypher 02_load_data.cypher`, see the CLI section). The web app never loads, wipes or reseeds data.

### Environment variables (names only, set in `app/.env`)
`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `APP_SECRET` (signs the session cookie), `COOKIE_SECURE` (true behind HTTPS), `CORS_ORIGINS` (optional). Generate a secret with `python3 -c "import secrets;print(secrets.token_urlsafe(48))"`. `.env` is git-ignored; never commit it.

### Demo logins (email only, no password)
| Role | Emails |
| --- | --- |
| STAFF | divya@courier.com, naveen@courier.com, karthik@courier.com |
| CUSTOMER | arun@example.com, priya@example.com, rahul@example.com, meera@example.com |

## Tests
```bash
source .venv/bin/activate
python -m pytest -q tests
```
Tests hit the real Aura database but only create customers 9001/9002 and what they send, delete everything afterwards, and assert the baseline counts (Branch 6, Customer 4, Employee 3, Package 7, Payment 5, Shipment 5, TrackingEvent 12) are restored.

## Features
Login with roles; dashboard; customers CRUD; book a shipment with several packages in one transaction; tracking timeline + graph picture; add tracking events; current status board; fewest-hops and fewest-km routes; hub impact; reports G7-G16; payments. Customers only see shipments they sent or received (enforced on the server with `EXISTS {}`; the menu also hides staff pages).

## UI notes
* Pages: Home, Track, My Parcels / All Parcels, Live Tracking, Delivered, Send (book), Routes, plus staff pages (Hub impact, Reports, Customers, Dashboard).
* The database stores scans, not GPS or coordinates. The "map" is a route drawn from the real scan places (booking branch, each scan location, receiver city) and is labelled as such. There is no ETA field either, so the ETA card shows the last scan and how long ago it was.
* "Upcoming" timeline steps are only the standard statuses not reached yet, with no invented times. "Delivered" only shows when the data says DELIVERED.
* Brand name is the `BRAND` constant at the top of `static/js/ui.js` (page titles and the login heading are plain HTML).
* Fonts (Nunito, Inter, Gaegu) load from Google Fonts; the app falls back to system fonts offline.

## Design notes
* Neo4j Aura Free has no NOT NULL / CHECK constraints, so required fields, positive weights/amounts and the status / type / mode whitelists are enforced in Pydantic (`backend/schemas.py`). Uniqueness comes from the database constraints; a `ConstraintError` becomes HTTP 409.
* New ids are `max(id)+1` computed inside the same write transaction; a race is caught by the unique constraint (customers retry, others return 409).
* Booking also writes the first `BOOKED` tracking event so the shipment shows in the status board. If staff book it, they are linked with `LOGGED`.
* If no amount is given, a demo rate card is used (`RATE_CARD` in `backend/config.py`).
* A DELIVERED or CANCELLED shipment accepts no more events (409).
* The payments report counts only `PAID` payments as paid (identical to G12 on the sample data).
* Restyling: edit only `static/css/theme.css`. Graph colours also come from its variables.

## Known limitations
* Login is **email only, no password** (demo). A real system needs passwords or SSO.
* Aura Free: no custom roles (`05_access_control_demo.cypher` is a design, not run), no property-existence constraints, instance pauses when idle (first request after a pause can be slow or return 503).
* The graph pictures load vis-network from a CDN (needs internet in the browser).
* Customers can look up another customer's id and name by exact email (needed to pick a receiver).

## Deploy (optional)
`docker compose up --build -d` serves on port 8000; put your reverse proxy (e.g. an `sslip.io` hostname) in front and set `COOKIE_SECURE=true`. The container only needs outbound access to Aura over `neo4j+s://`.

## Command line app (original)
```bash
cd app && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env     # fill in
python load_data.py ../01_constraints.cypher ../02_load_data.cypher   # first time only
python courier_app.py
```
Try `karthik@courier.com` (STAFF) and `arun@example.com` (CUSTOMER).

## Cypher scripts
Run `03_core_operations.cypher` and `04_graph_queries.cypher` one statement at a time in the Aura query tool. Route distances are approximate demo values.
