# Obscura headless browser, official release built WITH the `stealth` feature
# (TLS/HTTP2 Chrome impersonation + tracker blocking). The upstream Docker Hub
# image is built with `render` only, which leaves a non-Chrome TLS fingerprint.
FROM debian:bookworm-slim AS fetch
ARG TARGETARCH
ARG OBSCURA_VERSION=v0.2.5
ARG OBSCURA_SHA256_AMD64=d9175cf7573d0243fc303a6f1a3b68affc757af0b5549cacb018e9670988316c
ARG OBSCURA_SHA256_ARM64=e28ed5ff2dbabe8d820c7b1ef56e6005399aff15912c7774777719e66a021a32
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN set -eu; \
    case "${TARGETARCH:-amd64}" in \
      amd64) arch=x86_64;  sum="$OBSCURA_SHA256_AMD64" ;; \
      arm64) arch=aarch64; sum="$OBSCURA_SHA256_ARM64" ;; \
      *) echo "unsupported arch ${TARGETARCH}"; exit 1 ;; \
    esac; \
    curl -fsSLo /tmp/obscura.tgz "https://github.com/h4ckf0r0day/obscura/releases/download/${OBSCURA_VERSION}/obscura-${arch}-linux-stealth.tar.gz"; \
    echo "${sum}  /tmp/obscura.tgz" | sha256sum -c -; \
    mkdir /out && tar xzf /tmp/obscura.tgz -C /out

# Runs as uid 65532: page JavaScript executes in-process through V8.
FROM gcr.io/distroless/cc-debian12:nonroot
COPY --from=fetch /out/obscura /obscura
COPY --from=fetch /out/obscura-worker /obscura-worker
EXPOSE 9222
ENTRYPOINT ["/obscura"]
CMD ["serve", "--port", "9222", "--host", "0.0.0.0", "--stealth"]
