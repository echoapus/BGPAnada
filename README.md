# bgpx

BGP IPv4/IPv6 Unicast receiver with a live web UI — version 26.181.
Connects to a peer router, maintains an in-memory RIB, and streams everything to the browser via Server-Sent Events.

```bash
pip install bgpx
bgpx --local-as 65001 --router-id 192.0.2.2 --peer-ip 192.0.2.1 --peer-as 65000
# open http://localhost:8080
```

> **BGP session is IPv4-only.** `--peer-ip` and `--router-id` must be IPv4 addresses.  
> Routes received over that session can be IPv4 or IPv6 unicast.

---

## Features

- **Dual-mode connection** — races active-connect and passive-accept; first to succeed wins
- **IPv4 + IPv6 unicast** — prefix, next-hop, AS path, standard / well-known / large communities
- **4-byte ASN** — `AS_TRANS`, `CAP_4BYTE_ASN`, `AS4_PATH` (RFC 6793)
- **Hold-timer enforcement** — session resets on expiry
- **Web UI** — sortable route table, live log with filter chips, analytics, packet capture viewer

---

## Quick start

```bash
# Web UI only — configure the session in the browser
bgpx

# Auto-start a session
bgpx --local-as 65001 --router-id 10.0.0.1 \
     --peer-ip 10.0.0.2 --peer-as 65000

# With debug logging
bgpx --local-as 65001 --router-id 10.0.0.1 \
     --peer-ip 10.0.0.2 --peer-as 65000 \
     --log-level DEBUG
```

### Docker

```bash
docker build -t bgpx .
docker run --rm -p 179:179 -p 8080:8080 bgpx
```

---

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--local-as` | — | Local AS number |
| `--router-id` | — | Local BGP router-id (IPv4) |
| `--peer-ip` | — | BGP peer IP (IPv4) |
| `--peer-as` | — | BGP peer AS number |
| `--hold-time` | `90` | Hold time in seconds (`0` = disabled) |
| `--reconnect-delay` | `5` | Seconds before reconnecting after a drop |
| `--connect-timeout` | `5.0` | TCP connect timeout |
| `--active-retry-delay` | `1.0` | Delay between active connect attempts |
| `--host` | `0.0.0.0` | Web UI listen address |
| `--port` | `8080` | Web UI listen port |
| `--log-level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

> **Port 179** requires root or:
> ```bash
> sudo setcap cap_net_bind_service+ep $(readlink -f $(which python3))
> ```

---

## Web UI

Open `http://localhost:8080`. Session config is saved to `localStorage`.

| Panel | What it shows |
|---|---|
| Sidebar | Configure and start/stop the BGP session |
| **Total / Unicast** tabs | Paginated, sortable route table |
| **Analytics** tab | Family/AFI counts, top communities, origin AS, next-hops, prefix lengths |
| **Live Log** tab | SSE event stream — filter by SESSION / ANNOUNCE / WITHDRAW / ERROR / PCAP; click to expand JSON |
| **◉ Capture** | Start/stop `tcpdump` on BGP traffic (requires `tcpdump` on `$PATH`) |
| **⬇ Export** | Download the current table view as JSON |

Header indicators:
- **SSE dot** — green = live, pulsing yellow = reconnecting
- **State badge** — `IDLE` → `CONNECT` → `OPEN_SENT` → `OPEN_CONFIRMED` → `ESTABLISHED`

---

## RFC coverage

| RFC | Scope | Status |
|---|---|---|
| RFC 4271 | BGP-4 / IPv4 Unicast | FSM, timers, UPDATE, IPv4 unicast ✅ |
| RFC 4360 | Extended Communities | ✅ |
| RFC 4760 | MP-BGP / IPv6 Unicast | ✅ |
| RFC 6793 | 4-Byte ASN | OPEN capability, AS_PATH, AS4_PATH ✅ |

---

## Architecture

```
bgpx/
├── cli.py          entry point, component wiring
├── manager.py      session start / stop / restart
├── session.py      BGP FSM, UPDATE dispatch
├── rib.py          unicast RIB, stats, pagination
├── events.py       event history, SSE fan-out
├── capture.py      tcpdump subprocess wrapper
├── api.py          aiohttp routes, SSE, health endpoint
├── message/
│   ├── parser.py   BGP message parser (+ optional Rust PyO3 fast path)
│   ├── builder.py  OPEN / KEEPALIVE / NOTIFICATION builders
└── web/ui.html     single-file vanilla JS web UI
```

---

## Development

```bash
pip install -e ".[dev]"
pytest                  # 68 tests, pure Python
./test.sh               # Python + Rust PyO3 matrix (requires Cargo + maturin)
```

---

## Installation

For host deployment (systemd service, `/opt/bgpx`, port-179 capability) see [INSTALL.md](INSTALL.md).

---

## License

PolyForm Noncommercial License 1.0.0 — personal, research, educational, government, and public-benefit use permitted. Commercial use requires written permission.
