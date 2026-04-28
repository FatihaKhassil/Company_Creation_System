# Company Creation (Frappe App)

`company_creation` is a custom Frappe app that manages company formation requests, document
extraction workflows, and generated legal templates.

## Features

- End-user company creation request intake
- PDF extraction and analysis helpers
- Legal/administrative PDF template generation
- Web Form entrypoint for public request submission

## Tech Stack

- Frappe Framework (bench-managed dependency)
- Python 3.10+
- Packaging: `pyproject.toml` + `setup.py` (bench compatibility)

## Bench Installation

### 1) Get the app

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $YOUR_REPOSITORY_URL --branch main
```

### 2) Install on a site

```bash
bench --site $SITE_NAME install-app company_creation
```

### 3) Apply migrations

```bash
bench --site $SITE_NAME migrate
```

## Development Setup

Install tooling in the app folder:

```bash
cd apps/company_creation
pip install -r requirements.txt
pre-commit install
```

## Tests and Quality

Run app tests:

```bash
bench --site $SITE_NAME run-tests --app company_creation
```

Run linting from app directory:

```bash
ruff check .
```

Pre-commit hooks include:

- ruff
- eslint
- prettier
- pyupgrade

## Migration Guide (Naming Normalization)

This repository includes an idempotent patch to normalize Web Form identifiers to ASCII-safe slugs:

- Legacy Web Form name: `demande-de-création-d’entreprise`
- Canonical Web Form name: `demande-de-creation-entreprise`
- Patch module: `company_creation.patches.v0_0_1.normalize_web_form_name`

The patch is executed post model sync via `company_creation/patches.txt`.

## Runtime Assets

PDF templates used by generation utilities are shipped in:

- `company_creation/fixtures/tp-template.pdf`
- `company_creation/fixtures/RC-template.pdf`
- `company_creation/fixtures/DL-template.pdf`

## Troubleshooting

- If the app does not appear in Desk, run `bench clear-cache` then refresh Desk.
- If migration errors occur, re-run `bench --site $SITE_NAME migrate` and inspect patch logs.
- If static assets are stale, run `bench build` then hard refresh the browser.

## License

MIT
