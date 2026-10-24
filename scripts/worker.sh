#!/bin/sh
set -eu
until python manage.py migrate --check >/dev/null 2>&1; do sleep 5; done
while true; do
    if [ -n "${RESEND_API_KEY:-}" ] && [ -n "${EMAIL_FROM:-}" ]; then
        python manage.py send_notifications || true
    fi
    sleep 60
done
