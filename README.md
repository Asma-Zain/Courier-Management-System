# Courier Tracking System: Neo4j (DA3)

Graph-database version of the Courier Tracking System (BACSE202).

## What is in this folder
| File | Purpose |
| --- | --- |
| 01_constraints.cypher | Uniqueness constraints and indexes |
| 02_load_data.cypher | Branches, hubs, routes, employees, customers, shipments, packages, payments, tracking events |
| 03_core_operations.cypher | Create, read, update, delete and an integrity-violation demo |
| 04_graph_queries.cypher | 16 technology-specific queries (traversals, routes, subqueries, functions) |
| 05_access_control_demo.cypher | Roles and permissions (Neo4j Desktop / Enterprise only) |
| app/courier_app.py | Command-line application with STAFF / CUSTOMER roles |
| app/load_data.py | Runs .cypher files from Python, one statement at a time |

## Build and run (Windows 11, PowerShell)
1. Create a free Neo4j Aura instance (neo4j.com/cloud) or install Neo4j Desktop. Note the connection URI, username and password.
2. Install Python 3.10+ from python.org (tick "Add python.exe to PATH").
3. In PowerShell:

       cd neo4j_courier\app
       python -m venv .venv
       .venv\Scripts\Activate.ps1
       pip install -r requirements.txt
       copy .env.example .env
       notepad .env

   Fill in NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD. Never commit .env.
4. Load the schema and data:

       python load_data.py ..\01_constraints.cypher ..\02_load_data.cypher

   The last line printed should show the node counts: 6 Branch, 4 Customer, 3 Employee, 5 Shipment, 7 Package, 5 Payment, 12 TrackingEvent.
5. Run the app:

       python courier_app.py

   Try `karthik@courier.com` (STAFF) and `arun@example.com` (CUSTOMER).
6. For the demo queries, open Neo4j Browser (or the Aura Query tool) and run 03 and 04 one statement at a time.

## Notes
* The login is email-only for demonstration. A real system needs passwords or SSO.
* NOT NULL / CHECK style rules are enforced in the app because Neo4j property-existence constraints are Enterprise-only.
* Route distances in 02_load_data.cypher are approximate demo values.
