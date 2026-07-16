"""Tests for Unicast and FlowSpec RIB behavior."""

from bgpx.rib import FlowspecRIB


def test_rib_normalizes_legacy_match_values_on_output():
    rib = FlowspecRIB()
    route_id = rib.add_flowspec(
        "ipv4-flowspec",
        {"dst-prefix": "11.1.1.2/32", "tcp-flags": ["=63"]},
        ["discard"],
        "192.0.2.1",
    )

    route = rib.get(route_id)

    assert route["match"] == {
        "dst-prefix": "11.1.1.2/32",
        "tcp-flags": ["all(fin,syn,rst,psh,ack,urg)"],
    }
    assert rib.to_dict()["routes"][0]["match"] == route["match"]


def test_rib_remove_uses_normalized_match_values():
    rib = FlowspecRIB()
    rib.add_flowspec(
        "ipv4-flowspec",
        {"dst-prefix": "11.1.1.2/32", "tcp-flags": ["=63"]},
        ["discard"],
        "192.0.2.1",
    )

    removed = rib.remove_flowspec(
        "ipv4-flowspec",
        {
            "dst-prefix": "11.1.1.2/32",
            "tcp-flags": ["all(fin,syn,rst,psh,ack,urg)"],
        },
        "192.0.2.1",
    )

    assert removed
    assert rib.all() == []


def test_rib_stores_unicast_and_flowspec_without_id_collision():
    rib = FlowspecRIB()
    unicast_id = rib.add_unicast(
        "ipv4-unicast",
        "203.0.113.0/24",
        "192.0.2.1",
        next_hop="192.0.2.254",
        as_path=[65000, 65001],
        communities=["65000:100"],
    )
    flowspec_id = rib.add_flowspec(
        "ipv4-flowspec",
        {"dst-prefix": "203.0.113.0/24"},
        ["discard"],
        "192.0.2.1",
    )

    assert unicast_id != flowspec_id
    assert len(rib.all()) == 2
    assert rib.get(unicast_id)["communities"] == ["65000:100"]


def test_rib_page_and_stats_cover_full_rib():
    rib = FlowspecRIB()
    for prefix in ("203.0.113.0/24", "198.51.100.0/24", "192.0.2.0/24"):
        rib.add_unicast(
            "ipv4-unicast", prefix, "192.0.2.1",
            next_hop="192.0.2.254",
            as_path=[65000, 65001],
            communities=["65000:100"],
        )
    rib.add_flowspec(
        "ipv6-flowspec",
        {"dst-prefix": "2001:db8::/32", "ip-proto": ["=6"], "dst-port": ["=443"]},
        ["discard"],
        "192.0.2.1",
    )

    page = rib.page(family="unicast", page=2, page_size=2)

    assert page["count"] == 3
    assert len(page["routes"]) == 1
    assert page["stats"]["total"] == 4
    assert page["stats"]["unicast"] == 3
    assert page["stats"]["flowspec"] == 1
    assert page["stats"]["ipv4"] == 3
    assert page["stats"]["ipv6"] == 1
    assert page["stats"]["analytics"]["communities"] == [("65000:100", 3)]
    assert page["stats"]["analytics"]["origin_as"] == [("65001", 3)]

    rib.remove_unicast("ipv4-unicast", "203.0.113.0/24", "192.0.2.1")
    assert rib.stats()["unicast"] == 2
    assert rib.stats()["analytics"]["communities"] == [("65000:100", 2)]
