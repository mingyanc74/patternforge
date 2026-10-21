"""Catch Nginx's location-level add_header inheritance trap before deployment."""

from pathlib import Path


def test_security_headers_are_not_shadowed_by_location_cache_rules():
    config = (Path(__file__).resolve().parents[2] / "deploy/nginx.conf").read_text()
    assert "map $uri $cache_policy" in config
    assert "add_header Cache-Control $cache_policy always;" in config
    assert "add_header X-Frame-Options DENY always;" in config
    assert "frame-ancestors 'none'" in config
    # Every location appears after this point, including inline blocks.
    locations = config[config.index("    location /api/") :]
    assert "add_header " not in locations
    assert "location /assets/ { try_files $uri =404; }" in locations
