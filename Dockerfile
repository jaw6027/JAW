FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data DJANGO_DEBUG=0
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -f /run/secrets/build_ca ]; then \
      PIP_CERT=/run/secrets/build_ca pip install --no-cache-dir -r requirements.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi \
    && useradd --uid 10001 --create-home studio \
    && mkdir -p /data /app/staticfiles \
    && chown -R studio:studio /app /data
COPY --chown=studio:studio . .
USER studio
EXPOSE 8000
CMD ["sh", "scripts/start.sh"]
