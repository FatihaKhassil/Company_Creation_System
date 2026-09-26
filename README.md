# Company Creation (Frappe App)

[![Frappe](https://img.shields.io/badge/Frappe-Framework-0089FF?logo=frappe&logoColor=white)](https://frappeframework.com/)
[![ERPNext](https://img.shields.io/badge/ERPNext-Integration-29A745)](https://erpnext.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-TBD-lightgrey)](#license)

`company_creation` is a custom **Frappe** app, integrated into **ERPNext**, that automates and
simplifies the company formation process. It centralizes data collection, intelligent extraction,
and automated generation of the legal documents required to set up a company (in Morocco),
leveraging AI (OpenAI LLM API) to extract information from PDF files.

The module was built to reduce the manual, repetitive work of agents who assist clients through
company creation, by automating data collection and pre-filling official administrative documents.

## Table of Contents

- [Project Context](#project-context)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Core Doctypes](#core-doctypes)
- [Installation](#installation)
- [Development Setup](#development-setup)
- [Tests and Quality](#tests-and-quality)
- [Migration Guide (Naming Normalization)](#migration-guide-naming-normalization)
- [Runtime Assets](#runtime-assets)
- [Troubleshooting](#troubleshooting)
- [Author](#author)
- [License](#license)

## Project Context

Creating a company usually requires collecting a large amount of accurate, complete information
from the client, then manually re-entering it across several legal documents (articles of
association, Commercial Registry, Business Tax, Legal Deposit, etc.). This process is time
consuming, repetitive, and error-prone.

The `CompanyCreation` module addresses this by offering three ways to feed data into the system:

- **Direct client input** through a public Web Form.
- **Automatic extraction** from PDF files (national ID, supporting documents, articles of
  association, etc.) using an AI-powered extraction engine (OpenAI API).
- **Manual entry by the agent** directly in the dedicated Doctype.

All of this data feeds into a central document, `CompanyCreationRequest`, from which pre-filled
legal documents are generated automatically.

## Features

- Intake of company creation requests (client-side and agent-side).
- Universal PDF data extraction: targeted extraction (based on Doctype fields) or standard
  extraction (all relevant information).
- Extraction results stored in the generic `Document Analysis` Doctype.
- Review, correction, and editing of extracted data before it's used.
- Automatic generation of pre-filled legal documents:
  - Business Tax registration request (TP)
  - Commercial Registry declaration (RC)
  - Legal Deposit form (DL)
- Public Web Form entry point for client-submitted requests.
- Full history and traceability of extractions, records, and generated documents.
- Secure archiving of generated documents.

## Architecture Overview
<img width="552" height="760" alt="image" src="https://github.com/user-attachments/assets/c79b70f6-4979-4c36-921b-8d3282da9c39" />

## Tech Stack

| Layer                 | Technology                                   |
|------------------------|-----------------------------------------------|
| Backend                | Frappe Framework (bench-managed), Python 3.10+ |
| Frontend               | ERPNext auto-generated DocType UI, HTML, CSS, JavaScript, Bootstrap |
| Database               | MariaDB (ERPNext's default DBMS)              |
| AI / LLM               | OpenAI API (intelligent PDF data extraction)  |
| PDF text extraction    | pdfplumber                                    |
| PDF generation         | ReportLab, PyPDF2                             |
| Packaging              | `pyproject.toml` + `setup.py` (bench compatible) |

## Core Doctypes

- `CompanyCreationRequest` — central document gathering all information about the company to be created.
- `Document Analysis` — stores raw PDF extraction results (fields, values, confidence score).
- `Extraction Data Items` — individual extracted data items linked to a document analysis.
- `PDF Extraction Settings` — OpenAI API configuration (key, model, temperature, max tokens).
- `PDF Extraction Allowed Doctype` — list of Doctypes allowed for targeted extraction.
- `Bail details` — lease agreement details for the registered office.

## Installation

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

Run linting from the app directory:

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

- Legacy Web Form name: `demande-de-création-d'entreprise`
- Canonical Web Form name: `demande-de-creation-entreprise`
- Patch module: `company_creation.patches.v0_0_1.normalize_web_form_name`

The patch is executed post model sync via `company_creation/patches.txt`.

## Runtime Assets

PDF templates used by the generation utilities are shipped in:

- `company_creation/fixtures/tp-template.pdf`
- `company_creation/fixtures/RC-template.pdf`
- `company_creation/fixtures/DL-template.pdf`

## Troubleshooting

- If the app does not appear in Desk, run `bench clear-cache` then refresh Desk.
- If migration errors occur, re-run `bench --site $SITE_NAME migrate` and inspect the patch logs.
- If static assets are stale, run `bench build` then hard refresh the browser.

## Author

This project was developed by **Fatiha KHASSIL**, a student at **ENSIAS** (École Nationale
Supérieure d'Informatique et d'Analyse des Systèmes), D2S track, as part of her first-year
internship (PFA) at **KaSoft**.

- Supervised by: Mr. FAIZ Kamal
- Academic year: 2024–2025

