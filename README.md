# SmartBaku HoReCa ERP

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15_Alpine-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker_Compose-v2-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Pytest-5%20Passed%20(100%25)-success?logo=pytest&logoColor=white)](https://docs.pytest.org/)

**SmartBaku HoReCa ERP** is a high-density, enterprise resource planning system engineered for Azerbaijani hotels, restaurants, and café chains. It delivers real-time inventory management, atomic bill-of-materials recipe deduction, supplier tracking with strict 10-digit VÖEN validation, 18% ƏDV purchase waybill generation with ink-friendly A4 printing, and live Central Bank of Azerbaijan (`cbar.az`) exchange rate synchronization with offline caching.

---

## Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT BROWSERS                                   |
|   Desktop & Tablet UI (Inter + JetBrains Mono, Lucide Icons, Chart.js Analytics)   |
+------------------------------------------+----------------------------------------+
                                           | HTTP / REST (JSON + HTML)
                                           v
+-----------------------------------------------------------------------------------+
|                         SMARTBAKU FASTAPI APPLICATION (Port 8000)                |
|                                                                                   |
|  +------------------------+  +------------------------+  +---------------------+  |
|  |     Routers (src/)     |  |    Services (src/)     |  |   DatabaseManager   |  |
|  | - /api/ingredients     |  | - InventoryService     |  | - Threaded Pool     |  |
|  | - /api/recipes         |  | - RecipeEngine (Atomic)|  | - Auto Commit /     |  |
|  | - /api/suppliers       |  | - WaybillGenerator(ƏDV)|  |   Rollback Context  |  |
|  | - /api/waybills        |  | - CurrencySyncService  |  +----------+----------+  |
|  | - /api/currency        |  | - SupplierService      |             |             |
|  | - HTML Pages (Jinja2)  |  +------------------------+             |             |
|  +------------------------+                                         |             |
+---------------------------------------------------------------------|-------------+
                                                                      |
                   +--------------------------------------------------+
                   | psycopg2 (Connection Pool)
                   v
+--------------------------------------------------+      +-------------------------+
|             POSTGRESQL 15 (Port 5432)            |      |       CBAR.AZ API       |
|                                                  |      | (Central Bank of Azerb.)|
|  - ingredients (CHECK quantity >= 0)             |      |                         |
|  - recipes & recipe_items                        |<-----+ HTTPS XML Daily Rates   |
|  - suppliers (UNIQUE voen, 10 digits)            |      | (USD, EUR, TRY, RUB, GEL|
|  - waybills & waybill_items (18% ƏDV)            |      +-------------------------+
|  - currency_rates (Historical & Offline Cache)   |
+--------------------------------------------------+
```

---

## Core Invariants & Engineering Highlights

1. **Dual-Layer Non-Negative Stock Invariant:**
   - **Database Level:** `CHECK (quantity >= 0)` constraint guarantees inventory stock can never physically drop below zero.
   - **Application Level:** `RecipeEngine.cook()` acquires row locks (`SELECT ... FOR UPDATE OF i`) ordered strictly by `i.id ASC` to prevent concurrent deadlocks. It pre-validates that all required ingredients are sufficient; if any shortage occurs, it aborts immediately and raises `InsufficientStockError` (HTTP 409), triggering an atomic rollback before any mutations occur.

2. **Azerbaijani Tax & Legal Compliance (18% ƏDV):**
   - Automatically computes VAT using standard Azerbaijani rounding:
     $$\text{ƏDV Məbləği} = \text{round}\left(\text{Ara Cəm} \times \frac{18}{100}, 2\right), \quad \text{Yekun} = \text{Ara Cəm} + \text{ƏDV}$$
   - Generates sequential daily waybill numbers: `WB-YYYYMMDD-XXXX`.
   - Generates ink-friendly A4 print-ready documents (`/waybills/{id}/print`) with buyer/supplier VÖENs and dual signature blocks.

3. **Resilient Central Bank (`cbar.az`) XML Currency Parser:**
   - Fetches official exchange rates for `USD`, `EUR`, `TRY`, `RUB`, and `GEL`.
   - **Offline Resilience:** If `cbar.az` is unreachable, times out, or has connection issues, the service automatically falls back to the most recent cached rates in the `currency_rates` table.

4. **Linear / Stripe Dashboard UI Design:**
   - Sleek 240px fixed dark sidebar (`#0F172A`), slim 52px top utility bar, and `#F8FAFC` high-density workspace.
   - Zero emojis — 100% crisp Lucide SVG icons.
   - `Inter` typography for interface text; `JetBrains Mono` (`font-variant-numeric: tabular-nums`) for financial figures and quantities.
   - Interactive Chart.js horizontal bar chart displaying menu dish selling price vs. recipe ingredient cost.

---

## Directory Structure

```
smartbaku-horeca-erp/
├── docker-compose.yml          # Docker Compose orchestration (api + postgres)
├── Dockerfile                  # Python 3.11-slim container definition
├── requirements.txt            # Pinned production & testing dependencies
├── init.sql                    # PostgreSQL 15 schema DDL and realistic seed data
├── README.md                   # Enterprise technical documentation
│
├── src/
│   ├── __init__.py             # Package marker
│   ├── config.py               # Environment configuration (pydantic-settings)
│   ├── database.py             # Thread-safe PostgreSQL connection pool wrapper
│   ├── dependencies.py         # FastAPI dependency injection providers
│   ├── models.py               # Pydantic v2 schemas and global error envelope
│   ├── main.py                 # FastAPI application factory and error handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── inventory.py        # Stock CRUD, SELECT FOR UPDATE locking
│   │   ├── recipe.py           # Atomic cook engine with deadlock prevention
│   │   ├── waybill.py          # Purchase waybill and 18% ƏDV calculator
│   │   ├── currency.py         # CBAR XML parser and offline rate caching
│   │   └── supplier.py         # Supplier directory management
│   └── routers/
│       ├── __init__.py
│       ├── ingredients.py      # /api/ingredients endpoints
│       ├── recipes.py          # /api/recipes endpoints
│       ├── suppliers.py        # /api/suppliers endpoints
│       ├── waybills.py         # /api/waybills endpoints
│       ├── currency.py         # /api/currency endpoints
│       └── pages.py            # HTML Jinja2 view routes & print view
│
├── templates/
│   ├── base.html               # 240px dark sidebar + 52px topbar layout
│   ├── dashboard.html          # Metric cards, Chart.js analytics & low-stock alerts
│   ├── inventory.html          # High-density inventory management table
│   ├── recipes.html            # Master-detail recipe builder & cook engine
│   ├── suppliers.html          # Supplier directory with 10-digit VÖEN validation
│   ├── waybills.html           # Waybill manager with live tax calculation
│   └── waybill_print.html      # Formal A4 ink-friendly invoice/waybill print view
│
├── static/
│   ├── css/
│   │   ├── style.css           # High-density Enterprise SaaS stylesheet
│   │   └── print.css           # A4 portrait print overrides
│   └── js/
│       ├── app.js              # Fetch wrapper, toast notifications, currency ticker
│       ├── inventory.js        # Inventory actions and stock adjustment
│       ├── recipes.js          # Live margin calculation and availability check
│       ├── suppliers.js        # Strict VÖEN validation and CRUD
│       └── waybills.js         # Dynamic line items and locked AZN rate
│
└── tests/
    ├── __init__.py
    └── test_api.py             # Pytest automated integration test suite
```

---

## Quick-Start (Docker)

### Prerequisites
- Docker Engine 24+ & Docker Compose v2+

### 1. Launch the Full Stack
Run the following command from the project root:
```bash
docker compose up -d --build
```

### 2. Access the Application
- **Web Interface:** [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Reference:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Reset Database with Seed Data
To wipe and re-seed the PostgreSQL database back to its initial clean state:
```bash
docker compose down -v && docker compose up -d
```

---

## Automated Test Suite

The test suite validates inventory mutations, atomic multi-ingredient cook operations, strict VÖEN validation, 18% ƏDV math, and CBAR currency fallbacks.

Run the tests inside the container:
```bash
docker exec smartbaku_api pytest -v
```

**Test Results:**
```text
tests/test_api.py::test_inventory_crud_and_adjust PASSED                 [ 20%]
tests/test_api.py::test_atomic_recipe_cook_and_insufficient_stock PASSED [ 40%]
tests/test_api.py::test_supplier_voen_crud_and_uniqueness PASSED         [ 60%]
tests/test_api.py::test_waybill_edv_calculation_and_stock_receipt PASSED [ 80%]
tests/test_api.py::test_currency_rates_and_sync PASSED                   [100%]

========================= 5 passed, 1 warning in 0.77s =========================
```

---

## REST API Endpoint Summary

| Module | Method | Route | Description |
|---|---|---|---|
| **Ingredients** | `GET` | `/api/ingredients` | List all ingredients with supplier information |
| | `GET` | `/api/ingredients/low-stock` | Retrieve ingredients at or below minimum threshold |
| | `GET` | `/api/ingredients/{id}` | Retrieve single ingredient by ID |
| | `POST` | `/api/ingredients` | Create a new ingredient |
| | `PUT` | `/api/ingredients/{id}` | Update ingredient properties |
| | `DELETE`| `/api/ingredients/{id}` | Delete ingredient (restricted if linked to recipes) |
| | `POST` | `/api/ingredients/{id}/adjust-stock`| Atomic stock adjustment with negative pre-check |
| **Recipes** | `GET` | `/api/recipes` | List all recipes with cost per serving & margin |
| | `GET` | `/api/recipes/{id}` | Retrieve full recipe with ingredient bill-of-materials |
| | `POST` | `/api/recipes` | Create new menu recipe |
| | `PUT` | `/api/recipes/{id}` | Update recipe details or ingredient proportions |
| | `DELETE`| `/api/recipes/{id}` | Delete recipe (cascade deletes recipe items) |
| | `POST` | `/api/recipes/{id}/check` | Check ingredient availability for requested servings |
| | `POST` | `/api/recipes/{id}/cook` | **Atomic Cook:** Deduct stock or return 409 rollback |
| **Suppliers** | `GET` | `/api/suppliers` | List all suppliers |
| | `GET` | `/api/suppliers/{id}` | Retrieve supplier details |
| | `POST` | `/api/suppliers` | Register supplier with unique 10-digit VÖEN |
| | `PUT` | `/api/suppliers/{id}` | Update supplier details |
| | `DELETE`| `/api/suppliers/{id}` | Delete supplier |
| **Waybills** | `GET` | `/api/waybills` | List purchase waybills with tax calculations |
| | `GET` | `/api/waybills/{id}` | Retrieve waybill with line items |
| | `POST` | `/api/waybills` | Create waybill, compute 18% ƏDV, and increase stock |
| | `GET` | `/waybills/{id}/print` | Ink-friendly formal A4 printable invoice/waybill view |
| **Currency** | `GET` | `/api/currency/rates` | Retrieve latest cached or live exchange rates |
| | `POST` | `/api/currency/sync` | Force live synchronization with `cbar.az` |

---

## License & Attribution

Developed for **SmartBaku HoReCa ERP** &bull; Enterprise Hospitality and Catering Operations Management System &bull; Version 1.0.
