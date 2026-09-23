# Executed validation

Validated in this workspace on **2026-09-09**, using Windows, Python **3.10.0**, Django **5.2.17**, and SQLite. Dependencies were installed in `.venv/` from the pinned package set.

| Check | Result |
|---|---|
| `python manage.py makemigrations --settings=mattic_project.test_settings` | Generated real migrations for every model app |
| `python manage.py migrate --settings=mattic_project.test_settings --noinput` | All migrations applied successfully |
| `python manage.py seed_store --settings=mattic_project.test_settings` | Demo catalog/settings created; no credentials created |
| `python manage.py test --settings=mattic_project.test_settings --noinput` | **53 tests discovered: 51 passed, 2 skipped; 10.379 seconds** |
| `python manage.py check --settings=mattic_project.test_settings` | No issues; also passed during the final test run |
| `python manage.py check --deploy --fail-level WARNING` | No issues with an ephemeral check-only secret, DEBUG=False and PostgreSQL configuration |
| `python manage.py makemigrations --check --dry-run --settings=mattic_project.test_settings` | No changes detected |
| `python manage.py spectacular --settings=mattic_project.test_settings --file schema.yml --validate --fail-on-warn` | Passed without warnings/errors; **68 OpenAPI paths** |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 80 Python files already formatted; migrations excluded by configuration |
| `python -m pip check` | No broken requirements found |

There are **10 application migration files** covering the 20 domain models. The local development database is populated with demo products, variants, reference data and placeholder store/payment settings. During a subsequent local setup repair, `.env` was created with a generated secret and SQLite development settings, and the pinned dependencies were installed into the user's existing `virtenv` environment as well as `.venv`. The ignored `.env` is local-only; configure PostgreSQL and production settings before deployment.

## Environment limitations

- No PostgreSQL or Docker executable/service was detected. Actual PostgreSQL migration execution, Docker build/start and PostgreSQL row-lock tests were **not run locally**.
- Two explicit concurrency tests are skipped on SQLite: simultaneous verification of the same payment, and competing orders purchasing the same limited stock. They run on PostgreSQL in the supplied CI configuration.
- PostgreSQL deployment checks validate settings, not connectivity or database availability.
- Python 3.12 and the GitHub Actions workflow have **not been executed in this environment**. Docker/CI files specify Python 3.12 and PostgreSQL 16.
- No external merchant payment was sent or verified, and no application was deployed. Payment tests use generated images and demo merchant values.

The tested flows include registration/login/refresh/logout; owned addresses; public catalog and variant filters; cart and wishlist; transactional checkout and rollback; coupons; historical snapshots; private upload/download permissions; rejection/resubmission; single stock deduction on repeated verification; insufficient-stock rollback; fulfillment; delivered-purchaser review moderation; dashboard reporting and management; internal Django Admin; protected history on deletion; production JSON error responses; and idempotent demo seeding.


## React frontend integration (10 September 2026)

The storefront and owner dashboard are implemented in `frontend/`. The production build, ESLint, four unit tests and all four real Django/Chrome browser scenarios passed. The expanded backend suite found 54 tests: 52 passed and two PostgreSQL concurrency tests were skipped on SQLite. The public catalog now exposes verified best-seller counts, with a regression test that excludes unverified purchases and avoids multiplying sales across product variants. OpenAPI generation and changed-file Ruff checks passed.

See [frontend/VALIDATION.md](frontend/VALIDATION.md) for test coverage and desktop/mobile previews, and [frontend/README.md](frontend/README.md) for run commands and architecture.
