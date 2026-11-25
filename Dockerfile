FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKSPACE_DATA=/app/data
WORKDIR /app

RUN groupadd --system together \
    && useradd --system --gid together --home-dir /app together \
    && mkdir -p /app/data /app/public \
    && chown together:together /app/data
COPY server.py collaboration.py maintenance.py ./
COPY public/index.html public/shared.js public/features.js public/client.js public/layout.css public/features.css ./public/

USER together
VOLUME ["/app/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/', timeout=3).close()"
CMD ["python", "server.py", "--host", "0.0.0.0"]
