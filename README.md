# Di-VisioN ISO Toolkit

A Django-based Occupational Health & Safety (OHS) management platform for ISO compliance tracking.

## Features

- **Checklists** — CCV, PTO, FLRA, and Mobile Equipment inspection forms
- **CAPA Centre** — Corrective and Preventive Action tracking
- **Medical Centre** — Employee health records
- **Analytics Dashboard** — Site-wide safety metrics
- **Schedule Centre** — Safety inspection scheduling
- **Presets** — Configurable targets per tenant (CCV, PTO, FLRA, Employees, Objectives)
- **Training Matrix** — Employee certification tracking
- **Sites & Projects** — Multi-site management
- **Light / Dark Mode** — User preference toggle

## Tech Stack

- Python 3.x / Django 5.2
- SQLite (development) — PostgreSQL recommended for production
- Bootstrap-style custom CSS (no external CDN dependency)

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Deployment

For production deployment, set the following environment variables:

- `SECRET_KEY` — Django secret key
- `DEBUG` — Set to `False`
- `ALLOWED_HOSTS` — Your domain(s)
- `DATABASE_URL` — PostgreSQL connection string (optional)

---

*Part of the Di-VisioN family of industrial tools.*
