# bgpx

BGP Flowspec Receiver — RFC 4271 · RFC 8955 (IPv4) · RFC 8956 (IPv6) · RFC 6793 (4-byte ASN)

Receives BGP Flowspec rules from a peer router and maintains an in-memory RIB.
A live web UI shows routes, events, and packet captures in real time via Server-Sent Events.

---

## Features

- **Dual-mode connection** — races active-connect and passive-accept simultaneously; whichever succeeds first wins
- **IPv4 and IPv6 flowspec** — all NLRI component types (prefix, port, protocol, TCP flags, DSCP, fragment, flow-label)
- **All standard flowspec actions** — rate-limit (bps/pps), discard, redirect-to-VRF (AS2/IPv4/AS4), redirect-to-IP (IPv4/IPv6), DSCP mark, traffic-action
- **Unknown-flowspec-ec detection** — vendor or future-IANA extended communities in the flowspec EC range are flagged distinctly
- **4-byte ASN support** — `AS_TRANS`, `CAP_4BYTE_ASN`, `AS4_PATH` (RFC 6793)
- **Hold timer enforcement** — session resets if no message arrives within the negotiated hold time
- **JSON RIB persistence** — atomic file write on every RIB change (optional)
- **Web UI** — SSE-driven, no polling; sortable routes table, live log with filter chips, packet capture viewer
- **Docker-ready**

> **⚠️ BGP Session: IPv4 only**
> 
> The BGP session itself is IPv4-only. Both `--peer-ip` and `--router-id` must be IPv4 addresses. However, the receiver can accept and process IPv6 flowspec routes over this IPv4 BGP session.

---

## Requirements

- Python 3.11+
- `aiohttp >= 3.9`
- `tcpdump` on `$PATH` (optional, for packet capture)

---

## Installation

Quick start — see [INSTALL.md](INSTALL.md) for detailed setup, Docker, systemd, and troubleshooting:

```bash
pip install bgpx
```

Install from this source tree to `/opt/bgpx`:

```bash
sudo ./deploy.sh
```

The deploy script asks which port the Web UI should bind to. Press Enter to use `8080`, or pass the port noninteractively:

```bash
sudo ./deploy.sh --web-port 9090
```

Remove a `/opt/bgpx` deployment:

```bash
sudo ./uninstall.sh
```

Or with Docker:

```bash
docker build -t bgpx .
docker run --rm -p 179:179 -p 8080:8080 bgpx
```

> **⚠️ Port 179:** Requires root or `setcap cap_net_bind_service+ep $(readlink -f $(which python3))`. See [INSTALL.md](INSTALL.md#port-179-configuration).

---

## Usage

### Web UI only (configure via browser)

```bash
bgpx
# Open http://localhost:8080
```

After deploying with `deploy.sh`, open the port selected during deployment:

```bash
sudo ./deploy.sh --web-port 9090
# Open http://localhost:9090
```

### Auto-start session

```bash
bgpx --local-as 65001 --router-id 192.0.2.2 \
     --peer-ip 192.0.2.1 --peer-as 65000
```

### Full example

```bash
bgpx --local-as 65001 --router-id 10.0.0.1 \
     --peer-ip 10.0.0.2 --peer-as 65000 \
     --hold-time 90 \
     --json-output /tmp/routes.json \
     --log-level DEBUG
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `--local-as` | — | Local AS number |
| `--router-id` | — | Local BGP router-id (IPv4 address required) |
| `--peer-ip` | — | BGP peer IP address (IPv4 address required) |
| `--peer-as` | — | BGP peer AS number |
| `--hold-time` | `90` | BGP hold time in seconds (0 = disabled) |
| `--reconnect-delay` | `5` | Seconds to wait before reconnecting |
| `--connect-timeout` | `5.0` | TCP connect timeout in seconds |
| `--active-retry-delay` | `1.0` | Delay between active connect attempts |
| `--listen-port` | `179` | Passive listen port (needs root or `setcap`) |
| `--json-output` | — | Write RIB to this JSON file on every change |
| `--host` | `0.0.0.0` | Web UI listen address |
| `--port` | `8080` | Web UI listen port |
| `--log-level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

> **Port 179** requires root or:
> ```bash
> sudo setcap cap_net_bind_service+ep $(readlink -f $(which python3))
> ```

---

## Web UI

Open `http://localhost:8080` in a browser.

If installed with `deploy.sh`, use the Web UI port selected during deployment. The default is `8080`.

All data is pushed via **Server-Sent Events** — no polling, no page refresh needed.

| Panel | Description |
|---|---|
| Sidebar | Configure and start/stop the BGP session. Config is saved to `localStorage`. |
| **Routes** tab | Live flowspec RIB. Click any row to expand path attributes. Columns are sortable. |
| **Live Log** tab | Real-time event stream. Filter by SESSION / ANNOUNCE / WITHDRAW / ERROR / PCAP. Click an entry to expand JSON detail; `⎘ copy` copies it to clipboard. |
| **◉ Capture** | Start/stop `tcpdump` on BGP traffic. Output appears in the Live Log. |
| **⬇ Export** | Download the current RIB as `bgpx-routes.json`. |

The header shows:
- **SSE dot** — green = stream live, pulsing yellow = reconnecting
- **State badge** — current BGP FSM state (`IDLE` / `CONNECT` / `OPEN_SENT` / `OPEN_CONFIRMED` / `ESTABLISHED`)
- **Negotiated Session** panel — appears after OPEN handshake with peer router-id and negotiated hold time

---

## JSON RIB format

When `--json-output` is set, bgpx writes the RIB atomically on every change:

```json
{
  "count": 2,
  "routes": [
    {
      "id": "a3f1b2c4d5e6",
      "afi": "ipv4-flowspec",
      "peer": "10.0.0.2",
      "received_at": "2026-06-04T12:00:00.000000+00:00",
      "match": {
        "dst-prefix": "203.0.113.0/24",
        "ip-proto": ["=tcp(6)"],
        "dst-port": ["=80", "=443"]
      },
      "actions": ["discard"],
      "path_attributes": [...]
    }
  ]
}
```

---

## Architecture

```
bgpx/
├── cli.py          Entry point — argument parsing, wires components together
├── manager.py      Session lifecycle (start / stop / restart)
├── session.py      BGP FSM — dual-mode connect, OPEN/KEEPALIVE/UPDATE/NOTIFICATION
├── rib.py          Thread-safe in-memory Flowspec RIB, optional JSON persistence
├── events.py       Async event bus — emits to all SSE subscribers
├── capture.py      tcpdump subprocess wrapper
├── api.py          aiohttp app — web UI, SSE stream, command endpoints
├── constants.py    BGP/Flowspec protocol constants
├── message/
│   ├── parser.py   Incoming message parsing (OPEN, UPDATE, path attributes)
│   ├── builder.py  Outgoing message building (OPEN, KEEPALIVE, NOTIFICATION)
│   └── flowspec.py Flowspec NLRI + extended community parsing
└── web/
    └── ui.html     Single-file web UI (vanilla JS, SSE-driven)
```

---

## RFC coverage

| RFC | Title | Status |
|---|---|---|
| RFC 4271 | BGP-4 | Core FSM, timers, message types ✅; NOTIFICATION on errors ⚠️ |
| RFC 4360 | BGP Extended Communities | ✅ |
| RFC 4760 | Multiprotocol Extensions (MP-BGP) | ✅ |
| RFC 6793 | 4-Byte ASN | Outbound ✅; peer's 4-byte ASN from OPEN capabilities ⚠️ |
| RFC 8955 | IPv4 Flowspec | ✅ All component types and actions |
| RFC 8956 | IPv6 Flowspec | ✅ All component types and actions |

---

## IPv6 Support

**BGP session establishment**: IPv4 only. Both the local `--router-id` and `--peer-ip` must be IPv4 addresses.

**Flowspec routes**: Full IPv6 support. The receiver can receive and process IPv6 flowspec routes (RFC 8956) over the IPv4 BGP session. The routes themselves may match IPv6 prefixes and traffic.

Example: Connect via IPv4 (`10.0.0.1` ↔ `10.0.0.2`) but receive IPv6 flowspec rules that match `2001:db8::/32` traffic.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests cover the message parser, flowspec NLRI, extended communities, RIB, and session FSM.
