import re
import unittest
from pathlib import Path
from unittest.mock import patch

import vast_client
from vast_client import WrapperDepthExceededError


_FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


class VastClientParseTestCase(unittest.TestCase):
    def test_duration_parsing_formats(self) -> None:
        self.assertEqual(vast_client.parse_duration_to_seconds("00:00:30"), 30.0)
        self.assertEqual(vast_client.parse_duration_to_seconds("00:00:30.500"), 30.5)

    def test_add_correlator_appends_query_value(self) -> None:
        url = vast_client.add_correlator("https://ads.example.com/tag?foo=bar", correlator="12345")
        self.assertIn("foo=bar", url)
        self.assertIn("correlator=12345", url)

    @patch("vast_client.time.time", return_value=1713333333.123)
    def test_expand_ad_tag_macros_replaces_supported_placeholders(self, _: object) -> None:
        expanded = vast_client.expand_ad_tag_macros(
            "https://ads.example.com/tag?url=[referrer_url]&description_url=[description_url]&correlator=[timestamp]"
        )
        self.assertIn("url=http://localhost:8080", expanded)
        self.assertIn("description_url=http://localhost:8080", expanded)
        self.assertIn("correlator=1713333333123", expanded)

    @patch("vast_client.time.time", return_value=1713333333.123)
    def test_add_correlator_overrides_placeholder_correlator(self, _: object) -> None:
        url = vast_client.add_correlator(
            "https://ads.example.com/tag?correlator=[timestamp]&url=[referrer_url]",
            correlator="99999",
        )
        self.assertIn("correlator=99999", url)
        self.assertIn("url=http%3A%2F%2Flocalhost%3A8080", url)

    def test_inline_vast_parsing_selects_best_media_and_normalizes_macros(self) -> None:
        ads, wrapper = vast_client.parse_vast_xml(_load_fixture("vast_inline.xml"))
        self.assertIsNone(wrapper)
        self.assertEqual(len(ads), 1)
        ad = ads[0]
        self.assertEqual(ad.creative_id, "creative-inline-1")
        self.assertEqual(ad.media_url, "https://cdn.example.com/high.mp4")
        self.assertEqual(ad.duration_sec, 30.5)
        self.assertEqual(ad.click_through_url, "https://click.example.com/landing")
        self.assertRegex(ad.impression_urls[0], r"cb=\d{8}$")
        self.assertEqual(ad.tracking_events[0].event, "start")
        self.assertRegex(ad.tracking_events[0].url, r"cb=\d{8}$")

    def test_vmap_parser_extracts_valid_breaks_only(self) -> None:
        breaks = vast_client.parse_vmap_xml(_load_fixture("vmap_sample.xml"))
        self.assertEqual(len(breaks), 2)
        self.assertEqual(breaks[0].break_id, "preroll")
        self.assertEqual(breaks[1].time_offset, "00:10:00")


class VastClientFetchTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_wrapper_recursion_resolves_inline(self) -> None:
        wrapper_xml = _load_fixture("vast_wrapper.xml")
        inline_xml = _load_fixture("vast_inline.xml")

        async def fake_fetch(url: str) -> str:
            if "inline-feed" in url:
                return inline_xml
            return wrapper_xml

        ads = await vast_client._fetch_vast_recursive(
            "https://ads.example.com/wrapper",
            depth=0,
            max_wrapper_depth=5,
            fetcher=fake_fetch,
        )
        self.assertEqual(len(ads), 1)
        self.assertEqual(ads[0].media_url, "https://cdn.example.com/high.mp4")

    async def test_wrapper_depth_limit_raises_explicit_error(self) -> None:
        wrapper_xml = _load_fixture("vast_wrapper.xml")

        async def fake_fetch(_: str) -> str:
            return wrapper_xml

        with self.assertRaises(WrapperDepthExceededError):
            await vast_client._fetch_vast_recursive(
                "https://ads.example.com/wrapper",
                depth=0,
                max_wrapper_depth=1,
                fetcher=fake_fetch,
            )

    async def test_fetch_vast_uses_http_fetcher_path(self) -> None:
        inline_xml = _load_fixture("vast_inline.xml")
        with patch("vast_client._fetch_text", return_value=inline_xml) as mock_fetch:
            ads = await vast_client.fetch_vast("https://ads.example.com/inline")
            self.assertEqual(len(ads), 1)
            self.assertTrue(mock_fetch.await_count >= 1)

    async def test_fetch_vmap_uses_http_fetcher_path(self) -> None:
        vmap_xml = _load_fixture("vmap_sample.xml")
        with patch("vast_client._fetch_text", return_value=vmap_xml):
            breaks = await vast_client.fetch_vmap("https://ads.example.com/vmap")
            self.assertEqual(len(breaks), 2)


if __name__ == "__main__":
    unittest.main()
