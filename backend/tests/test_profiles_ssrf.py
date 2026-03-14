"""Unit tests for SSRF-prevention helper _is_safe_image_url in profiles API."""

from __future__ import annotations

import pytest

from app.api.profiles import _is_safe_image_url


class TestIsSafeImageUrl:
    """Tests for the _is_safe_image_url SSRF guard."""

    # --- valid URLs ---

    def test_public_https_url_is_safe(self):
        assert _is_safe_image_url("https://media.licdn.com/dms/image/profile.jpg") is True

    def test_https_cdn_url_is_safe(self):
        assert _is_safe_image_url("https://example.com/photo.png") is True

    # --- scheme checks ---

    def test_http_url_is_not_safe(self):
        """HTTP (non-TLS) URLs are rejected."""
        assert _is_safe_image_url("http://example.com/photo.jpg") is False

    def test_ftp_url_is_not_safe(self):
        assert _is_safe_image_url("ftp://files.example.com/photo.jpg") is False

    def test_empty_string_is_not_safe(self):
        assert _is_safe_image_url("") is False

    def test_plain_path_is_not_safe(self):
        assert _is_safe_image_url("/profiles/user-1.jpg") is False

    # --- loopback / localhost ---

    def test_localhost_is_not_safe(self):
        assert _is_safe_image_url("https://localhost/internal") is False

    def test_127_0_0_1_is_not_safe(self):
        assert _is_safe_image_url("https://127.0.0.1/secret") is False

    def test_ipv6_loopback_is_not_safe(self):
        assert _is_safe_image_url("https://::1/admin") is False

    # --- private IP ranges ---

    def test_rfc1918_10_block_is_not_safe(self):
        assert _is_safe_image_url("https://10.0.0.1/internal") is False

    def test_rfc1918_172_block_is_not_safe(self):
        assert _is_safe_image_url("https://172.16.0.1/internal") is False

    def test_rfc1918_192_168_block_is_not_safe(self):
        assert _is_safe_image_url("https://192.168.1.100/camera") is False

    # --- edge cases ---

    def test_url_with_whitespace_is_handled(self):
        """Leading/trailing whitespace should be stripped before parsing."""
        assert _is_safe_image_url("  https://example.com/photo.jpg  ") is True

    def test_url_missing_host_is_not_safe(self):
        assert _is_safe_image_url("https://") is False
