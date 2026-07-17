"""Tests for unicast RIB behavior."""

import re

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


def test_rib_reports_churn_and_as_path_analysis():
    rib = UnicastRIB()
    route_id = rib.add_unicast(
        "ipv4-unicast", "203.0.113.0/24", "192.0.2.1", as_path=[65000, 65100, 65000],
    )

    stats = rib.stats()
    assert stats["churn"]["1m"] == {"announce": 1, "withdraw": 0}
    assert stats["analytics"]["path_lengths"] == [("3", 1)]
    assert stats["analytics"]["as_loops"] == [("detected", 1)]

    rib.remove_unicast("ipv4-unicast", "203.0.113.0/24", "192.0.2.1")
    assert rib.stats()["churn"]["1m"] == {"announce": 1, "withdraw": 1}


def test_rib_lookup_returns_only_the_longest_matching_prefix():
    rib = UnicastRIB()
    rib.add_unicast("ipv4-unicast", "203.0.0.0/16", "192.0.2.1")
    rib.add_unicast("ipv4-unicast", "203.0.113.0/24", "192.0.2.1")
    rib.add_unicast("ipv6-unicast", "2001:db8::/32", "2001:db8::1")

    assert [route["prefix"] for route in rib.lookup("203.0.113.9")] == ["203.0.113.0/24"]
    assert [route["prefix"] for route in rib.lookup("2001:db8::2")] == ["2001:db8::/32"]
    assert rib.lookup("198.51.100.1") == []


def test_rib_page_filters_an_exact_community():
    rib = UnicastRIB()
    rib.add_unicast("ipv4-unicast", "203.0.113.0/24", "192.0.2.1", communities=["65000:100"])
    rib.add_unicast("ipv4-unicast", "198.51.100.0/24", "192.0.2.1", communities=["65000:200"])

    page = rib.page(community="65000:100")
    assert page["count"] == 1
    assert page["routes"][0]["prefix"] == "203.0.113.0/24"


def test_rib_page_filters_an_as_path_regex():
    rib = UnicastRIB()
    rib.add_unicast("ipv4-unicast", "203.0.113.0/24", "192.0.2.1", as_path=[65000, 65100, 65200])
    rib.add_unicast("ipv4-unicast", "198.51.100.0/24", "192.0.2.1", as_path=[65000, 65200])

    page = rib.page(as_path_regex=re.compile(r"^651\d{2}$"))
    assert page["count"] == 1
    assert page["routes"][0]["prefix"] == "203.0.113.0/24"
    assert rib.page(as_path_regex=re.compile(r"^65500$"))["count"] == 0
