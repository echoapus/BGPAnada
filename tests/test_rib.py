"""Tests for unicast RIB behavior."""

from bgpx.rib import UnicastRIB


def test_rib_stores_pages_and_removes_unicast_routes():
    rib = UnicastRIB()
    route_id = rib.add_unicast(
        "ipv4-unicast", "203.0.113.0/24", "192.0.2.1",
        next_hop="192.0.2.254", as_path=[65000, 65001], communities=["65000:100"],
    )

    assert rib.get(route_id)["communities"] == ["65000:100"]
    assert rib.page()["stats"]["unicast"] == 1
    assert rib.remove_unicast("ipv4-unicast", "203.0.113.0/24", "192.0.2.1") == route_id
    assert rib.all() == []
