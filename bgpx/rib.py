"""In-memory unicast RIB."""

import hashlib
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from itertools import islice

log = logging.getLogger(__name__)


def _route_id(afi: str, peer: str, route: dict) -> str:
    """Deterministic ID scoped by AFI and peer."""
    canonical = json.dumps(
        [afi, peer, route],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(canonical.encode()).hexdigest()[:12]


# ponytail: threading.Lock removed because bgpx is purely single-threaded asyncio
class UnicastRIB:
    def __init__(self):
        self._routes: dict[str, dict] = {}
        self._counts = Counter()
        self._analytics = {
            name: Counter()
            for name in (
                "communities", "origin_as", "next_hops", "prefix_lengths",
            )
        }
        self._changes = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def add_unicast(
        self,
        afi: str,
        prefix: str,
        peer: str,
        next_hop: str = "",
        as_path: list[int] | None = None,
        communities: list[str] | None = None,
        path_attributes: list[dict] | None = None,
    ) -> str:
        route_id = _route_id(afi, peer, {"prefix": prefix})
        entry = {
            "id": route_id,
            "family": "unicast",
            "afi": afi,
            "peer": peer,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "prefix": prefix,
            "next_hop": next_hop,
            "as_path": as_path or [],
            "communities": communities or [],
        }
        if path_attributes is not None:
            entry["path_attributes"] = path_attributes
        old = self._routes.pop(route_id, None)
        if old:
            self._remove_stats(old)
        self._routes[route_id] = entry
        self._add_stats(entry)
        log.debug("RIB %s [%s] id=%s peer=%s prefix=%s",
                  "UPDATE" if old else "ADD", afi, route_id, peer, prefix)
        self._changed()
        return route_id

    def remove_unicast(self, afi: str, prefix: str, peer: str) -> str | None:
        return self._remove_id(
            _route_id(afi, peer, {"prefix": prefix})
        )

    def clear_peer(self, peer: str) -> int:
        keys = [k for k, v in self._routes.items() if v["peer"] == peer]
        for k in keys:
            self._remove_stats(self._routes.pop(k))
        if keys:
            log.info(f"RIB cleared {len(keys)} route(s) from peer {peer}")
            self._changed()
        return len(keys)

    def all(self) -> list[dict]:
        return [dict(r) for r in self._routes.values()]

    def by_afi(self, afi: str) -> list[dict]:
        return [
            dict(r)
            for r in self._routes.values()
            if r["afi"] == afi
        ]

    def get(self, route_id: str) -> dict | None:
        route = self._routes.get(route_id)
        return dict(route) if route else None

    def clear_all(self) -> int:
        count = len(self._routes)
        self._routes.clear()
        self._counts.clear()
        for values in self._analytics.values():
            values.clear()
        if count:
            log.info(f"RIB cleared all {count} route(s)")
            self._changed()
        return count

    def to_dict(self) -> dict:
        routes = [dict(r) for r in self._routes.values()]
        return {"count": len(routes), "routes": routes}

    def stats(self) -> dict:
        return {
            "total": len(self._routes),
            "unicast": self._counts["unicast"],
            "ipv4": self._counts["ipv4"],
            "ipv6": self._counts["ipv6"],
            "analytics": {
                name: values.most_common(5)
                for name, values in self._analytics.items()
            },
        }

    def page(
        self,
        page: int = 1,
        page_size: int = 50,
        sort: str = "received_at",
        ascending: bool = False,
    ) -> dict:
        allowed_sort = {"id", "afi", "prefix", "next_hop", "peer", "received_at"}
        if sort not in allowed_sort:
            sort = "received_at"

        values = self._routes.values()
        if sort == "received_at":
            ordered = values if ascending else reversed(values)
            routes = iter(ordered)
            total = len(self._routes)
        else:
            routes = sorted(
                values,
                key=lambda route: str(route.get(sort, "")).lower(),
                reverse=not ascending,
            )
            total = len(routes)
        page = max(1, page)
        page_size = min(500, max(1, page_size))
        start = (page - 1) * page_size
        return {
            "page": page,
            "page_size": page_size,
            "count": total,
            "routes": [
                dict(route)
                for route in islice(routes, start, start + page_size)
            ],
            "stats": self.stats(),
        }

    def iter_routes(self):
        for route in self._routes.values():
            yield dict(route)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _remove_id(self, route_id: str) -> str | None:
        removed = self._routes.pop(route_id, None)
        if not removed:
            return None
        self._remove_stats(removed)
        log.debug("RIB DEL id=%s", route_id)
        self._changed()
        return route_id

    def _changed(self) -> None:
        self._changes += 1
        if self._changes % 10_000 == 0:
            log.info("RIB contains %s routes", f"{len(self._routes):,}")

    def _add_stats(self, route: dict) -> None:
        self._counts["unicast"] += 1
        self._counts["ipv6" if str(route["afi"]).startswith("ipv6") else "ipv4"] += 1
        for name, values in self._route_metrics(route).items():
            self._analytics[name].update(values)

    def _remove_stats(self, route: dict) -> None:
        self._counts.subtract(["unicast"])
        self._counts.subtract([
            "ipv6" if str(route["afi"]).startswith("ipv6") else "ipv4"
        ])
        self._counts += Counter()
        for name, values in self._route_metrics(route).items():
            self._analytics[name].subtract(values)
            self._analytics[name] += Counter()

    def _route_metrics(self, route: dict) -> dict[str, list]:
        metrics = {name: [] for name in self._analytics}
        metrics["communities"] = route.get("communities", [])
        path = route.get("as_path", [])
        if path:
            metrics["origin_as"] = [str(path[-1])]
        if route.get("next_hop"):
            metrics["next_hops"] = [route["next_hop"]]
        prefix_length = str(route.get("prefix", "")).partition("/")[2]
        if prefix_length:
            metrics["prefix_lengths"] = [f"/{prefix_length}"]
        return metrics
