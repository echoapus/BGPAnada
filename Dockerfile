FROM rust:1.85-slim AS rust-build

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages --no-cache-dir maturin

WORKDIR /build
COPY bgpx_rust ./bgpx_rust
RUN maturin build --release --manifest-path bgpx_rust/Cargo.toml --interpreter python3 --out /wheels

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=rust-build /wheels /wheels
RUN pip install --no-cache-dir -e . && pip install --no-index --find-links /wheels bgpx_rust

EXPOSE 8080

ENTRYPOINT ["bgpx"]
CMD ["--host", "0.0.0.0", "--port", "8080"]
