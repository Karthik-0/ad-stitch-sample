import unittest
from pathlib import Path

from manifest_builder import (
    build_master,
    build_variant_live_only,
    build_variant_with_preroll,
    get_next_media_sequence,
)
from models import AdPod, ConditionedAd

class TestMasterPlaylistBuilder(unittest.TestCase):
    def setUp(self):
        fixtures_dir = Path(__file__).parent / "fixtures"
        self.master_playlist = (fixtures_dir / "master_playlist.m3u8").read_text()
        self.session_id = "test-session-uuid"
        self.live_variant = """#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:423
#EXT-X-PLAYLIST-TYPE:EVENT
#EXT-X-INDEPENDENT-SEGMENTS
#EXTINF:6.000000,
#EXT-X-PROGRAM-DATE-TIME:2026-04-16T11:56:03.894+0530
video-720p423.ts
#EXTINF:6.000000,
#EXT-X-PROGRAM-DATE-TIME:2026-04-16T11:56:09.894+0530
video-720p424.ts
#EXTINF:6.000000,
#EXT-X-PROGRAM-DATE-TIME:2026-04-16T11:56:15.894+0530
video-720p425.ts
#EXTINF:6.000000,
#EXT-X-PROGRAM-DATE-TIME:2026-04-16T11:56:21.894+0530
video-720p426.ts
#EXTINF:6.000000,
#EXT-X-PROGRAM-DATE-TIME:2026-04-16T11:56:27.894+0530
video-720p427.ts
#EXTINF:6.000000,
#EXT-X-PROGRAM-DATE-TIME:2026-04-16T11:56:33.894+0530
video-720p428.ts
#EXTINF:6.000000,
#EXT-X-PROGRAM-DATE-TIME:2026-04-16T11:56:39.894+0530
video-720p429.ts
"""
        self.pod = AdPod(
            pod_id="pod-1",
            ads=[
                ConditionedAd(
                    creative_id="creative-1",
                    duration_sec=10.083333,
                    renditions={
                        "720p": [("720p_0.ts", 6.0), ("720p_1.ts", 4.083333)],
                    },
                )
            ],
            total_duration=10.083333,
        )
    
    def test_master_rewrite(self):
        rewritten = build_master(self.master_playlist, self.session_id)
        self.assertIn("/session/test-session-uuid/240p.m3u8", rewritten)

    def test_live_only_uses_recent_window_and_preserves_segment_tags(self):
        rewritten = build_variant_live_only(self.live_variant, self.session_id)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:424", rewritten)
        self.assertIn("#EXT-X-PROGRAM-DATE-TIME:2026-04-16T11:56:09.894+0530", rewritten)
        self.assertIn("/session/test-session-uuid/seg/live/video-720p424.ts", rewritten)
        self.assertNotIn("/session/test-session-uuid/seg/live/video-720p423.ts", rewritten)

    def test_next_media_sequence_tracks_live_edge(self):
        self.assertEqual(get_next_media_sequence(self.live_variant), 430)

    def test_midroll_injection_starts_at_requested_splice_sequence(self):
        rewritten, _ = build_variant_with_preroll(
            self.live_variant,
            self.session_id,
            self.pod,
            "720p",
            "unused",
            splice_at_sequence=430,
        )
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:430", rewritten)
        self.assertIn("/session/test-session-uuid/seg/ad/720p/0", rewritten)
        self.assertNotIn("/session/test-session-uuid/seg/live/video-720p423.ts", rewritten)
        self.assertNotIn("/session/test-session-uuid/seg/live/video-720p429.ts", rewritten)

    def test_pod_with_multiple_ads_stitches_all_ad_segments(self):
        multi_ad_pod = AdPod(
            pod_id="pod-multi",
            ads=[
                ConditionedAd(
                    creative_id="creative-a",
                    duration_sec=6.0,
                    renditions={"720p": [("a_0.ts", 6.0)]},
                ),
                ConditionedAd(
                    creative_id="creative-b",
                    duration_sec=4.0,
                    renditions={"720p": [("b_0.ts", 4.0)]},
                ),
            ],
            total_duration=10.0,
        )

        rewritten, _ = build_variant_with_preroll(
            self.live_variant,
            self.session_id,
            multi_ad_pod,
            "720p",
            "unused",
            splice_at_sequence=430,
        )
        self.assertIn("#EXT-X-CUE-OUT:DURATION=10.0", rewritten)
        self.assertIn("/session/test-session-uuid/seg/ad/720p/0", rewritten)
        self.assertIn("/session/test-session-uuid/seg/ad/720p/1", rewritten)

if __name__ == "__main__":
    unittest.main()
