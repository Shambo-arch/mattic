# Suit and Tie Fashion Shop: Django API

Store name: **Suit and Tie Fashion Shop**. Intended production website: **https://suitandtiefashionshop.com**. The frontend metadata and domain links, Django host configuration, API documentation and seeded catalog use this identity. Applying migrations updates the previous store/demo brand names while preserving their records and product relationships. Domain registration, DNS and HTTPS hosting must be configured when deploying.

A men's fashion REST API with **CUSTOMER** and **ADMIN** roles, variant inventory, and **manual MTN Mobile Money screenshot verification**. The React storefront and owner dashboard live in a separate repository and consume this API. Payments use manual screenshot verification; there is no automatic MTN API integration.

The existing `mattic_project` Django configuration package is retained. Django Admin is available for internal administration, alongside a complete dashboard API.

Administrative access is restricted to the active `ADMIN` account matching `DASHBOARD_ADMIN_EMAIL` in the root `.env`. A blank setting disables administrative access. Other emails cannot be promoted to ADMIN, and stale admin flags do not bypass the dashboard, private payment proof, or Django Admin checks. Restart Django after changing this setting; use the configured email when running `createsuperuser`. Passwords are entered interactively and stored as Django password hashes.

Set the frontend's `VITE_API_BASE_URL` to this API's `/api/v1` URL and add the frontend origin to `CORS_ALLOWED_ORIGINS`.

## Project layout

```text
mattic_project/          Environment settings, URLs, WSGI/ASGI, test configuration
accounts/               Email user model, JWT authentication, customer addresses
catalog/                Categories, brands, sizes, colors, products, images, variants
cart/                   Customer/guest carts and stock validation services
wishlist/               Customer wishlist
promotions/             Coupons and Decimal discount calculations
orders/                 Checkout, historical snapshots, fulfillment transitions
payments/               Private proofs, merchant settings, atomic verification
reviews/                Delivered-purchaser reviews and moderation
dashboard/              Admin CRUD APIs, inventory, customer reports, sales reports
core/                   Shared validation, permissions, storage, response/schema wrappers
  management/commands/  seed_store
tests/                  API, security, transaction and PostgreSQL concurrency tests
schema.yml              Generated OpenAPI contract
.github/workflows/      Python 3.12 / PostgreSQL CI checks
Dockerfile
railway.toml            Railway build, migrate-on-deploy and health check config
compose.yaml
requirements.txt        Exact dependency versions, including transitive dependencies
.env.example            Configuration template; contains no real credentials
```

Every model app includes committed migrations. Money uses `DecimalField`; cart prices are calculated properties rather than stored stale copies. Public JSON represents money as decimal strings.

## Requirements

- Python **3.12 recommended**, with Python 3.10 compatibility for the supplied Windows environment.
- PostgreSQL 14+; Docker Compose uses PostgreSQL 16.
- SQLite is an explicitly enabled development/test fallback. Its lack of row locks makes it unsuitable for live inventory/payment concurrency.
- No paid services are needed. Public images and private payment screenshots use separate local storage roots by default.

Dependencies are pinned in `requirements.txt`. Django uses the 5.2 LTS line; see the [official support/download page](https://www.djangoproject.com/download/) and [DRF compatibility announcement](https://www.django-rest-framework.org/community/3.16-announcement/).

## Install on Windows / PowerShell

Run from this repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; from pathlib import Path; p=Path('.env'); p.write_text(p.read_text().replace('replace-with-a-long-random-secret-before-running', secrets.token_urlsafe(64)))"
```

If only Python 3.10 is installed, use `python -m venv .venv` for the first command. Activation is optional: use `.\.venv\Scripts\python.exe` instead of `python` if PowerShell blocks activation. Preserve an existing `.env`; only copy the template for initial setup.

On macOS/Linux, use `python3.12 -m venv .venv`, `source .venv/bin/activate`, and `cp .env.example .env`, then the same Python commands.

If your existing terminal shows `(virtenv)`, you can keep that environment. Install dependencies with `virtenv\Scripts\python.exe -m pip install -r requirements.txt` and run commands with `virtenv\Scripts\python.exe manage.py ...`. Packages installed in `.venv` are separate from `virtenv`. Check the selected interpreter with `python -c "import sys; print(sys.executable)"` if Django cannot be imported.

In Windows Command Prompt, use `set DEBUG=True` to enable local development for the current terminal; the PowerShell equivalent is `$env:DEBUG = 'True'`. An inherited `DEBUG` variable overrides the value in `.env`.

### PostgreSQL

Create a database and dedicated account through `psql` or your PostgreSQL administration tool:

```sql
CREATE ROLE mattic_app WITH LOGIN PASSWORD 'replace-with-your-own-password';
CREATE DATABASE mattic_shop OWNER mattic_app;
```

Set `DB_NAME=mattic_shop`, `DB_USER=mattic_app`, `DB_PASSWORD`, `DB_HOST=localhost`, and `DB_PORT=5432` in `.env`. Set `USE_SQLITE=False`. An optional `DATABASE_URL` takes precedence over the individual PostgreSQL variables. Use a separate test database account with `CREATEDB` when running Django tests against PostgreSQL; production application accounts need not have that privilege.

Then run:

```powershell
python manage.py migrate
python manage.py check
python manage.py createsuperuser
python manage.py seed_store
python manage.py runserver
```

`createsuperuser` asks for an email and password and creates an ADMIN account. No demo credentials or customer accounts are created automatically.

### Local SQLite fallback

After installing dependencies and creating `.env`, use these environment overrides for the current PowerShell session:

```powershell
$env:DEBUG = 'True'
$env:USE_SQLITE = 'True'
python manage.py migrate
python manage.py seed_store
python manage.py createsuperuser
python manage.py runserver
```

Alternatively put `DEBUG=True` and `USE_SQLITE=True` in `.env`. Existing process environment variables override `.env`, so clear any conflicting environment values. Never serve the application with `test_settings`: it uses a fast, insecure test-only password hasher.

### URLs

- Swagger: http://127.0.0.1:8000/api/docs/
- ReDoc: http://127.0.0.1:8000/api/redoc/
- OpenAPI: http://127.0.0.1:8000/api/schema/
- Internal Django Admin: http://127.0.0.1:8000/django-admin/
- Public catalog: http://127.0.0.1:8000/api/v1/products/

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Required application secret; no runtime fallback in real settings |
| `DEBUG` | Defaults to false; enables local media serving when true |
| `ALLOWED_HOSTS` | Comma-separated backend hostnames |
| `CORS_ALLOWED_ORIGINS` | Explicit browser frontend origins |
| `CSRF_TRUSTED_ORIGINS` | Origins trusted for Django Admin session forms |
| `USE_SQLITE` | Defaults to false; may only be used with debug enabled |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection |
| `DATABASE_URL` | Optional connection URL overriding PostgreSQL variables |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | Defaults: 15 minutes / 7 days |
| `DEFAULT_CURRENCY` | Demo seed currency; defaults to RWF |
| `DEMO_MOMO_CODE` | Demo seed placeholder; defaults to `123456` |
| `PUBLIC_STORAGE_BACKEND`, `PRIVATE_STORAGE_BACKEND` | Replaceable Django storage classes |
| `SECURE_SSL_REDIRECT` | Defaults to true outside debug; configure appropriately behind a TLS proxy |

Runtime shipping, currency, low-stock threshold and merchant instructions are stored in the database. Exactly one active store settings record and one active payment settings record are allowed. To replace an active record, deactivate it first, or edit it directly.

## Model relationships

| Area | Models and behavior |
|---|---|
| Identity | Email-login User, many owned Addresses; one default address per user |
| Catalog | Category hierarchy, Brand, Size, Color, Product, many ProductImages and ProductVariants |
| Inventory | Unique SKU and product/size/color combination; nonnegative variant stock |
| Shopping | One Cart and Wishlist per user; unique items per variant/product |
| Orders | Order and OrderItems with immutable historical name, SKU, size, color, category and price snapshots |
| Payment | One Payment per Order; merchant instruction snapshot and private proof image |
| Promotions | Coupon validity, usage limits, minimum spend, percentage/fixed discount |
| Reviews | One review per customer/product; delivered purchase required; moderation default |
| Settings | StoreSettings and StorePaymentSettings |

Products/variants referenced by orders are protected from deletion. Deactivate products instead. Variant identity cannot change after an order references it; price and stock can still be updated. UUID-suffixed slugs and order numbers avoid unsafe “last row plus one” generation. Order numbers use `MEN-YYYYMMDD-<16 hex characters>`.

## API conventions

All JSON endpoints use this envelope (including paginated `data.results`):

```json
{"success": true, "message": "Request successful.", "data": {"id": 1}}
```

Errors preserve HTTP status codes and use `{"success": false, "message": "Request failed.", "errors": {...}}`. Validation failures use 400, unauthenticated requests 401, role denial 403, absent or inaccessible owned objects 404, and invalid state transitions 409. DELETE returns an empty 204 response. OpenAPI, documentation pages and authenticated image downloads use their native formats.

Send ordinary request bodies as `application/json`; send image uploads as `multipart/form-data`. Authenticate with `Authorization: Bearer <access>`. Swagger's Authorize control accepts the access token. Role, owner, amounts and payment status are assigned by the server, regardless of submitted client values.

Refresh tokens rotate and the previous token is blacklisted. Logout blacklists the submitted refresh token belonging to the current user. An already-issued access token remains usable until its short expiration; password changes invalidate access tokens through SimpleJWT's password-revocation check. Registration never grants ADMIN. Profile email is immutable through `/auth/me/`.

### Customer/public endpoints

All paths below are relative to `/api/v1/`.

| Method | Path | Access / purpose |
|---|---|---|
| POST | `auth/register/`, `auth/login/`, `auth/token/refresh/` | Public authentication |
| POST | `auth/logout/` | Logged-in user; body contains `refresh` |
| GET, PATCH | `auth/me/` | Own profile |
| CRUD | `addresses/`, `addresses/{id}/` | CUSTOMER-owned addresses |
| GET | `products/`, `products/{id-or-slug}/` | Public catalog |
| GET | `categories/`, `brands/`, `colors/`, `sizes/` | Active reference data |
| GET | `store/`, `payment-instructions/` | Active public configuration |
| GET | `cart/` | Items, subtotal, total quantity |
| POST | `cart/items/` | `variant`, `quantity`; repeat add increases quantity |
| PATCH, DELETE | `cart/items/{id}/` | Update quantity or remove owned item |
| DELETE | `cart/clear/` | Empty own cart |
| GET | `wishlist/` | Own saved products |
| POST | `wishlist/items/` | `product`; duplicate is idempotent |
| DELETE | `wishlist/items/{id}/` | Remove owned item |
| POST | `checkout/` | `shipping_address_id` for accounts or `guest_address` for guests; optional `coupon_code`, `customer_note` |
| GET | `orders/`, `orders/{id}/` | Own orders and payment instructions |
| POST | `orders/{id}/payment-proof/` | Multipart `screenshot`, optional `transaction_reference` |
| GET | `payments/{id}/screenshot/` | Customer/guest owner or ADMIN; private file stream |
| GET, POST | `reviews/` | Public approved reviews / CUSTOMER review creation |

Product filters: `search`, `category` (ID or slug, including descendants), `brand`, `size`, `color`, `min_price`, `max_price`, `in_stock`, `featured`. Use `ordering=-created_at` for newest, `ordering=price` or `ordering=-price`, and `page=2` for pagination. Size/color/price filters match the same available variant. Price sorting uses the lowest available variant price, falling back to the product's sale/base price. In-stock means an available variant with active size/color and positive stock.

### Guest checkout

An anonymous browser generates a cryptographically random 32-byte secret, encoded as 64 lowercase hexadecimal characters, and sends it in `X-Guest-Token` on cart, checkout, order and payment-proof requests. Only its SHA-256 hash is stored with guest carts/orders. The secret is not included in URLs or API responses. Authenticated requests use the account owner instead of the guest header. Guest access does not permit account, wishlist, review or dashboard operations.

Guest checkout submits `guest_address` with `full_name`, `phone_number`, `province`, `district` and `sector`; `country` defaults to Rwanda. Optional fields are `cell`, `village`, `street_or_landmark` and `additional_information`. It creates an order without a user account or saved address. The storefront retains the private session in local browser storage. Guests return through `/orders` using the same browser; clearing its site data removes access. Guest and signed-in carts remain separate.

### Dashboard endpoints

Every path under `/api/v1/dashboard/` requires an active **ADMIN** user. Database Django permissions and `is_staff` alone do not grant API access.

| Method | Path | Purpose |
|---|---|---|
| GET | `summary/` | Sales, counts, low stock, recent orders, best sellers |
| CRUD | `products/`, `categories/`, `brands/`, `colors/`, `sizes/` | Catalog management |
| CRUD | `images/` | Upload, primary selection, reorder via `sort_order`, delete |
| CRUD | `variants/` or `inventory/` | Variant identity, availability, price and absolute stock quantity |
| CRUD | `coupons/` | Promotions; `times_used` is server-controlled |
| CRUD | `settings/`, `payment-settings/` | Store and MoMo instructions |
| GET | `orders/`, `orders/{id}/` | All customer orders |
| POST, PATCH | `orders/{id}/transition/` | Body: `status`, optional `admin_note` |
| GET | `payments/`, `payments/{id}/` | Payment queue and proof URL |
| POST | `payments/{id}/verify/` | Verify manually; optional `admin_note` |
| POST | `payments/{id}/reject/` | Reject manually; optional `admin_note` |
| GET | `customers/`, `customers/{id}/` | Customer data, order counts, paid spend, recent orders |
| GET, PATCH, DELETE | `reviews/`, `reviews/{id}/` | Review moderation via `is_approved` |
| GET | `reports/sales/` | Revenue, paid order count/average, products/categories, daily trend |

Inventory filters: `search`, `product`, `variant`, `low_stock`, `out_of_stock`, `is_available`. Order filters: `status`, `payment_status`, `customer`, `order_number`, `search`, `date_from`, `date_to`. Payment filters: `status`, `order`, `search`, `date_from`, `date_to`. Dates use `YYYY-MM-DD`; ranges are inclusive and follow Africa/Kigali time. Sales revenue is grouped by confirmation date; new customers/order counts use their creation date. Best seller `gross_item_sales` excludes order discounts and shipping; total revenue includes both as charged to the customer.

## Manual Mobile Money workflow

1. ADMIN publishes store/payment settings. Payments use Mobile Money number **0784888458**, with screenshot verification. The demo seed remains labeled as test data.
2. A customer or guest adds a variant to the cart and submits delivery details at checkout.
3. Checkout recalculates current prices, discount and shipping under a database transaction. It creates the order, line snapshots and a PENDING payment, then clears the cart. Payment instructions are in `data.payment.instructions_snapshot`.
4. CUSTOMER pays the displayed merchant externally, then uploads an image. Payment becomes SUBMITTED; order becomes PAYMENT_SUBMITTED / PENDING_VERIFICATION.
5. ADMIN checks the screenshot against actual merchant transaction records. A screenshot alone is not automatic confirmation.
6. Verify locks the order, payment and variants, rechecks stock, deducts inventory, and marks VERIFIED / PAID / CONFIRMED atomically. Repeating verify is safe and does not deduct twice. Competing orders cannot reduce PostgreSQL stock below zero.
7. Reject marks the payment REJECTED and returns the order to PENDING_PAYMENT with payment_status REJECTED. The customer may upload a replacement.
8. ADMIN advances CONFIRMED → PROCESSING → SHIPPED → DELIVERED. The delivered buyer can submit a review, which appears publicly only after approval.

An unpaid order can be cancelled, releasing its coupon usage once. Paid orders cannot be cancelled through this MVP: a separately audited refund workflow is required, so cancellation cannot accidentally report a refund that never occurred. Returns/refunds are intentionally outside scope. Orders are not automatically expired; ADMIN should cancel abandoned unpaid orders. Stock is **not reserved at checkout**. If stock is insufficient when a paid screenshot is reviewed, verification leaves the payment submitted; the merchant must arrange fulfillment or handle the customer's payment externally.

Shipping is a configurable flat fee. Free shipping applies when the subtotal after coupon discount meets the configured threshold. Coupon usage is reserved at checkout and released only on unpaid cancellation. Store/payment currencies must match. No tax engine is included.

## Payment proof storage

Public catalog images live under `media/`, served at `/media/` only with DEBUG enabled. Payment screenshots live under **`private_media/`**, which is never included in public media URLs. Files use generated UUID names. Uploads require JPG/JPEG, PNG or WEBP with matching real content, at most 5 MB and 20 million pixels. Pillow verifies decoding; arbitrary file extensions and mismatched content are rejected.

The API returns an authenticated `screenshot_url`, not a storage path. A frontend should fetch that URL with the account Bearer token or private `X-Guest-Token` header, convert the response to a blob, and create an object URL for preview. Do not append credentials to image query strings. The internal Django Admin has a separate protected session-authenticated proof viewer. Rejected proof replacements delete the old file after successful commit; a failed database transaction can leave an unreferenced upload, so production storage maintenance should remove unreferenced objects according to your retention policy.

`STORAGES['default']` and `STORAGES['private']` use Django's storage API. Add the chosen provider package and backend options to switch to S3/Cloudinary. Keep the private bucket nonpublic; authenticated downloads must continue to read through the private storage backend. Do not expose `private_media/` from a web server.

## Tests and verification

The SQLite suite requires no PostgreSQL server and uses an isolated test database:

```powershell
python manage.py test --settings=mattic_project.test_settings --noinput
python manage.py check --settings=mattic_project.test_settings
python manage.py makemigrations --check --dry-run --settings=mattic_project.test_settings
python manage.py spectacular --settings=mattic_project.test_settings --file schema.yml --validate --fail-on-warn
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

To exercise real PostgreSQL row-lock races, configure the PostgreSQL test connection and set `$env:USE_SQLITE = 'False'` before running the same test command. Both concurrency tests run automatically on PostgreSQL and explicitly skip on SQLite. The included CI workflow installs Python 3.12, starts PostgreSQL 16, applies migrations, runs deployment checks, executes the full suite and validates OpenAPI. CI has not been executed merely by creating the workflow file.

The suite covers the complete customer/admin lifecycle, JWT rotation/logout, owner isolation, input validation, catalog filtering, dashboard CRUD, checkout rollback, historical snapshots, coupons, private uploads, repeated verification, insufficient stock, rejected resubmission, fulfillment, moderated reviews, reports and seed idempotence. See [VALIDATION.md](VALIDATION.md) for this workspace's executed results and limitations.

## Docker

Create `.env` with a generated secret and nonempty PostgreSQL password first. Then:

```powershell
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose run --rm web python manage.py seed_store
docker compose up -d web
```

The web container runs Gunicorn on Python 3.12 as a non-root user. Named volumes preserve the database and uploads. Compose is a local/deployment starting point; add TLS termination and production public-media storage before launch. Migrations are explicit release steps, not run by every Gunicorn worker.

## Production notes

Use PostgreSQL, a unique secret, `DEBUG=False`, explicit host/origin lists and HTTPS. With these values the settings enable secure cookies, HSTS, SSL redirect and nosniff. Configure proxy HTTPS forwarding only if the proxy strips untrusted forwarded headers. Run `python manage.py check --deploy --fail-level WARNING`, migrate, and collect static files. WhiteNoise serves collected static assets; use a web server or object storage for public media.

Limit request bodies at the reverse proxy as well as in Django. Set up database and upload backups, private image retention, monitoring and restore procedures. DRF throttles are basic application protection; use an edge rate limit/shared cache across workers if needed. Run `python manage.py flushexpiredtokens` periodically to clean expired JWT records.

Inventory, orders, carts and payments are read-only as raw Django Admin records to protect service invariants; payment verification/rejection actions call the same services as the dashboard. Use dashboard APIs for stock changes and fulfillment. Django Admin offers model browsing, product/reference/settings editing, payment proof viewing and review moderation. Superuser creation and account privilege management remain internal operations.

There are no background email notifications, automatic MTN calls, staff roles, tax calculations, frontend pages or external refund processing. The dashboard payment queue is the administrator's notification mechanism. These choices follow the backend scope and avoid relying on external paid services.

## Deploy on Railway

`railway.toml` builds the Dockerfile, runs `migrate` before each deploy and health-checks `/healthz/`. Add a PostgreSQL database and a volume mounted at `/data`, then set these service variables:

| Variable | Value |
| --- | --- |
| `SECRET_KEY` | Long random string |
| `DEBUG` | `False` |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `MEDIA_ROOT` / `PRIVATE_MEDIA_ROOT` | `/data/media` / `/data/private_media` |
| `SERVE_MEDIA` | `True` |
| `RAILWAY_RUN_UID` | `0` (lets the app write to the volume) |
| `DASHBOARD_ADMIN_EMAIL` | Owner email |
| `CORS_ALLOWED_ORIGINS` | Frontend origin(s), e.g. `https://suitandtiefashionshop.com` |

The Railway public domain is added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` automatically; add custom domains to `ALLOWED_HOSTS`.
