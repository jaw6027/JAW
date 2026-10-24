# Deployment and operations

## Architecture and scope

Django, SQLite, and optimized local photo storage on a single host. Docker Compose shares the persistent `studio_data` volume between web and worker. Caddy optionally provides HTTPS. This is suitable for a small personal journal. Do not use ephemeral/serverless disks, multiple independent hosts, or network-mounted SQLite. Managed PostgreSQL and private object storage would be a separate upgrade for larger traffic.

No public launch or paid purchase is implied by testing. Review costs and obtain owner approval first.

## Prepare the host

Install Docker with Compose on Linux. Clone this repository and check out the website branch. Copy `.env.example` to `.env` and keep it private. Docker Compose loads it; direct Python commands require exported variables.

Set:

- `DJANGO_DEBUG=0`
- `DJANGO_SECRET_KEY`: generate privately with `python -c 'import secrets; print(secrets.token_urlsafe(64))'`. Keep it stable across deployments.
- `DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com`
- `CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com`
- `SITE_URL=https://your-domain.com`
- `DATA_DIR=/data`
- `DOMAIN=your-domain.com` (used by Caddy)
- `RESEND_API_KEY` and `EMAIL_FROM` when your sender domain is verified. Leave empty for email preview mode.

Replace domain examples with real values. Use comma-separated lists without spaces.

```sh
docker compose build
docker compose up -d web worker
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py check --deploy
```

The web process migrates the database and collects static assets before starting Gunicorn. The worker waits for the schema and checks emails every minute. Port 8000 binds only to loopback and production redirects HTTP to HTTPS; test through your trusted reverse proxy. Do not enable debug to bypass HTTPS setup.

On a managed network with a private certificate authority, the Docker build accepts an optional BuildKit trust-bundle secret: `docker build --secret id=build_ca,src=/path/to/trusted-ca-bundle.pem -t petal-polish:local .`. Use only the environment's authoritative CA bundle, configure its supported proxy/DNS route, and keep TLS verification enabled. Ordinary public-network builds need no secret.

Optional samples: `docker compose exec web python manage.py seed_samples`. It preserves existing content. No owner is automatically created in production. Local development credentials and content are excluded from the image.

## Connect the domain and HTTPS — after approval

Point the domain's DNS A record to the server's public IPv4 address. Only add AAAA if IPv6 works. Add a `www` record only if serving that name too. The included Caddy configuration serves `DOMAIN`; edit it to include aliases as needed. Open host ports 80 and 443.

After owner approval:

```sh
docker compose --profile public up -d
```

Caddy handles certificate issuance and renewal. Keep Gunicorn behind Caddy: Django trusts the proxy's HTTPS header. Never expose port 8000 publicly or forward untrusted headers through another proxy. Rate limits currently use the direct peer IP, so visitors behind one proxy share conservative hourly limits. Configure trusted real-IP processing and edge rate limits if traffic grows; do not blindly trust visitor-supplied forwarding headers.

## Data, backups, and updates

`studio_data` holds the database and photos. It survives container replacement and ordinary `docker compose down`. **Do not run `docker compose down -v`: that destroys data.** Never serve this folder publicly; Django protects draft photo URLs.

Schedule encrypted, off-host backups of the full volume. For a consistent simple snapshot, stop web and worker writes, copy the volume through the host's backup tooling, then restart them. Preserve `db.sqlite3` and `photos/` together. Set retention and test restoration to a separate private instance. Deleting a design hides its photo URLs, but orphaned files and old backups need a separate retention cleanup; obtain approval before destructive cleanup.

Back up before updating, then pull reviewed code and run:

```sh
docker compose build
docker compose up -d web worker
docker compose logs --tail=100 web worker
```

Monitor disk space, application errors, backup restoration, pending email counts, and Resend delivery/bounce logs. Processes restart separately from retained data. Keep the web and worker services enabled after host restarts.

## Email behavior and limits

Use a real Resend account and verified sender domain. Actual provider acceptance is recorded; inbox delivery is not asserted. Message content is snapshotted at first delivery attempt and retry keys stay stable. Ambiguous attempts over 23 hours are blocked for manual review because Resend idempotency expires after 24 hours. Check provider logs before reconciling such items. Unsubscribed recipients and unpublished designs are skipped.

There is no webhook endpoint or automated bounce suppression. Review bounces in Resend and deactivate invalid addresses in the studio; add verified webhook handling before growing to larger volume. Keep credentials in host settings or private `.env`, never Git. Use long owner passwords; change development credentials if migrating a local database. Review the privacy notice and local requirements with the owner.

## Launch checklist

Verify layouts on phones and desktop over the real HTTPS domain. Test uploads, order, cover selection, preview, publish, unpublish, delete, and real retailer links. Confirm logged-out visitors cannot read drafts or draft photos. Subscribe with your own address, confirm, receive exactly one notification, edit/retry without a duplicate, and unsubscribe. Restart containers and verify posts and photos remain. Test backup restoration. Review domain, email, privacy, affiliate disclosures, costs, and launch approval.

The deployment security check intentionally leaves the optional HSTS subdomain and preload switches off. They produce two warnings. Enable them only after confirming every subdomain supports HTTPS and understanding the long-lived preload commitment; they are not required for this site's own HTTPS policy.
