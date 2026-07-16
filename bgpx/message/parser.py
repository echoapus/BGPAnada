"""Rust BGP parser bindings."""

try:
    import bgpx_rust as _rust
    parse_header = _rust.parse_header
    parse_open = _rust.parse_open
    parse_update_details = _rust.parse_update_details
except (ImportError, AttributeError) as exc:
    raise RuntimeError("bgpx requires the compiled bgpx_rust parser extension") from exc
