import unittest

from fastapi import HTTPException

from routes.control import _calculate_splice_sequence, _normalize_ad_tag


class ControlSchedulingTestCase(unittest.TestCase):
    def test_uses_last_live_sequence_when_available(self) -> None:
        # 30s delay at 6s segments => +5 segments
        self.assertEqual(
            _calculate_splice_sequence(
                last_live_sequence=430,
                fallback_next_sequence=500,
                duration_seconds=30,
            ),
            435,
        )

    def test_falls_back_to_next_sequence_without_playback_anchor(self) -> None:
        # 25s delay at 6s segments => ceil(4.166..) => +5 segments
        self.assertEqual(
            _calculate_splice_sequence(
                last_live_sequence=None,
                fallback_next_sequence=500,
                duration_seconds=25,
            ),
            505,
        )

    def test_normalize_ad_tag_accepts_https(self) -> None:
        self.assertEqual(
            _normalize_ad_tag(" https://example.com/vast.xml "),
            "https://example.com/vast.xml",
        )

    def test_normalize_ad_tag_empty_is_none(self) -> None:
        self.assertIsNone(_normalize_ad_tag("   "))
        self.assertIsNone(_normalize_ad_tag(None))

    def test_normalize_ad_tag_rejects_non_http(self) -> None:
        with self.assertRaises(HTTPException):
            _normalize_ad_tag("ftp://example.com/adtag")


if __name__ == "__main__":
    unittest.main()
