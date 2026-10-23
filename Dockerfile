# SMard Web Crawler HTTP API. Browser engines run in their own containers
# (Obscura, Crawl4AI), so this image needs Playwright's driver but no browsers.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    SMARD_HOME=/data

WORKDIR /app
COPY pyproject.toml README.md constraints.txt ./
COPY smard_crawler ./smard_crawler
RUN pip install --no-cache-dir -c constraints.txt ".[server,mcp]" \
    && useradd --system --uid 10001 --home /data smard \
    && mkdir -p /data/output && chown -R smard /data

USER smard
VOLUME ["/data"]
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8787), 3)"
CMD ["smard-crawler", "serve", "--host", "0.0.0.0", "--port", "8787"]
