# Petal & Polish — nail art journal

A complete Django website for a nail artist: an editorial homepage, searchable gallery, design pages, private owner studio, photo uploads, and double opt-in email subscriptions. **Petal & Polish is an editable default name**, not an assumed real business. Cream, blush, and plum styling works on desktop and mobile, with local fonts and no tracking scripts.

## Run locally

Requires Python 3.11+; developed using Python 3.12.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_samples
python manage.py create_local_owner
python manage.py runserver 0.0.0.0:8000
```

On Windows, activate using `.venv\Scripts\activate`. The background email worker targets Linux. Open port 8000 in your local browser. Your private dashboard is at `/owner/`. The generated development login is saved privately in **`data/local-owner-access.txt`**, never in Git or logs. Open that file to sign in; the setup never changes an existing owner.

All included designs are **labeled samples with SVG illustrations**, not the owner's nail art. Supplies are examples without invented purchase URLs. Replace them through the studio.

## Owner and deployment guides

- [OWNER_GUIDE.md](OWNER_GUIDE.md): posting, photos, product links, subscribers, and launch requirements.
- [DEPLOYMENT.md](DEPLOYMENT.md): Docker, persistent storage, HTTPS, backups, and custom domains.

## Validate

```sh
python manage.py collectstatic --noinput
python manage.py check
python manage.py test studio -v 2
python -m unittest discover -s tests -v
```

The website suite exercises owner permissions, draft and photo privacy, image optimization, filters, affiliate links, consent, CSRF, spam limits, confirmation, unsubscribe, honest email failure, and notification idempotency. Email provider responses are mocked; actual inbox delivery requires your verified Resend account.

## Persistence and email

The SQLite database and optimized photos are under `DATA_DIR` (default `data/`). Mount this directory on persistent disk in production and back it up. The Docker configuration shares one named volume between web and email worker. Do not serve the data folder as public static files: draft photos require authorization.

Without `RESEND_API_KEY` and `EMAIL_FROM`, subscription forms clearly show preview mode. Addresses are not saved and no messages are sent. The owner can see a visual email preview at `/owner/email-preview/`.

With a verified Resend sender configured, visitors receive a real confirmation email and must confirm before receiving updates. Run `python manage.py send_notifications` every minute; the supplied Docker worker does this automatically. Durable queue entries, immutable message snapshots, and Resend idempotency keys prevent duplicates on edits or ordinary retries. Uncertain attempts older than 23 hours stop for manual review before provider deduplication expires. Provider acceptance is distinct from inbox delivery.

See `.env.example` for settings. Docker Compose reads `.env`; direct Python commands use exported variables and do **not** automatically read `.env`. Never commit credentials.

The original standalone `jaw` greeting CLI remains available; the website runs through `manage.py`.
