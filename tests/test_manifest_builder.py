"""
Unit tests for manifest builder: rewrite, live passthrough, and pre-roll injection.
"""

import unittest
from unittest.mock import Mock
from pathlib import Path

from manifest_builder import (
    build_master,
    build_variant_live_only,
    build_variant_with_preroll,
)
from models import AdPod, ConditionedAd, AdState


class TestMasterPlaylistBuilder(unittest.TestCase):
    """Test master playlist parsing and variant URI rewriting."""
    
    def setUp(self):
        """Load test fixtures."""
        fixtures_dir = Path(__file__).parent / "fixtures"
        self.master_playlist = (fixtures_dir / "master_playlist.m3u8").read_text()
        self.session_id = "test-session-uuid"
    
    def test_master_rewrite_creates_session_variant_uris(self):
        """
        Task 5.2: Master playlist builder rewrites variant URIs to session endpoints.
        
        Given a live master with variant URIs,
        When build_master is called with a session ID,
        Then each variant URI is rewritten to /session/{sid}/{rendition}.m3u8
        """
        rewritten = build_master(self.master_playlist, self.session_id)
        
        # Should contain session-scoped variant URIs
        self.assertIn("/session/test-session-uuid/240p.m3u8", rewritten)
        self.assertIn("#EXT-X-VERSION:3", rewritten)
    
    def test_master_preserves_metadata_tags(self):
        """Master builder preserves HLS metadata and tags."""
        rewritten = build_master(self.master_playlist, self.session_id)
        
        # Metadata should be preserved
        self.assertIn("#EXTM3U", rewritten)
        self.assertIn("#EXT-X-VERSION", rewritten)
        self.assertIn("#EXT-X-TARGETDURATION", rewritten)


class TestVariantPlaylistLiveOnly(unittest.TestCase):
    """Test variant playlist live-only passthrough with segment rewriting."""
    
    def setUp(self):
        """Load test fixtures."""
        fixtures_dir = Path(__file__).parent / "fixtures"
        self.variant_playlist = (fixtures_dir / "variant_playlist_live.m3u8").read_text()
        self.session_id = "test-session-uuid"
    
    def test_variant_live_only_rewrites_segment_uris(self):
        """
        Task 5.2: Variant builder rewrites live segment filenames to stitcher routes.
        
        Given a live variant with segment filenames,
        When build_variant_live_only is called,
        Then each segment is rewritten to /session/{sid}/seg/live/{filename}
        """
        rewritten = build_variant_live_only(self.variant_playlist, self.session_id)
        
        # Should contain live segment routes
        self.assertIn("/session/test-session-uuid/seg/live/video-240p0.ts", rewritten)
        self.assertIn("/session/test-session-uuid/seg/live/video-240p1.ts", rewritten)
        self.assertIn("/session/test-session-uuid/seg/live/video-240p3.ts", rewritten)
    
    def test_variant_live_only_preserves_extinf(self):
        """Live-only variant preserves #EXTINF duration markers."""
        rewritten = build_variant_live_only(self.variant_playlist, self.session_id)
        
        # Durations should be preserved
        self.assertIn("#EXTINF:10.0,", rewritten)
    
    def test_variant_live_only_preserves_metadata(self):
        """Live-only variant preserves HLS metadata."""
        rewritten = build_variant_live_only(self.variant_playlist, self.session_id)
        
        self.assertIn("#EXTM3U", rewritten)
        self.assertIn("#EXT-X-VERSION:3", rewritten)


class TestVariantPlaylistWithPreroll(unittest.TestCase):
    """Test variant playlist pre-roll injection and state promotion."""
    
    def setUp(self):
        """Setup test fixtures and mock pod."""
        fixtures_dir = Path(__file__).parent / "fixtures"
        self.variant_playlist = (fixtures_dir / "variant_playlist_live.m3u8").read_text()
        self.session_id = "test-session-uuid"
        
        # Create mock pod with conditioned ad
        self.mock_pod = self._create_mock_pod()
    
    def _create_mock_pod(self) -> AdPod:
        """Create a mock AdPod for pre-roll injection testing."""
        # Mock conditioned ad with rendition segments
        conditioned_ad = Mock(spec=ConditionedAd)
        conditioned_ad.creative_id = "creative-123"
        conditioned_ad.renditions = {
            "240p": [
                ("ad-segment-0.ts", 5.0),
                ("ad-segment-1.ts", 4.0),
            ]
        }
        
        pod = Mock(spec=AdPod)
        pod.conditioned_ads = [conditioned_ad]
        pod.duration_sec = 9.0
        
        return pod
    
    def test_variant_with_preroll_injects_ad_segments(self):
        """
        Task 5.3: Pre-roll injection adds ad segments with discontinuity markers.
        
        Given a pending ad pod and live variant,
        When build_variant_with_preroll is called,
        Then the result includes ad segment URIs with #EXT-X-DISCONTINUITY markers
        """
        rewritten, should_promote = build_variant_with_preroll(
            self.variant_playlist,
            self.session_id,
            self.mock_pod,
            "/storage/ads",
        )
        
        # Should have discontinuity markers
        self.assertIn("#EXT-X-DISCONTINUITY", rewritten)
        
        # Should have ad segment URIs
        self.assertIn(f"/session/{self.session_id}/seg/ad/240p/0", rewritten)
        self.assertIn(f"/session/{self.session_id}/seg/ad/240p/1", rewritten)
        
        # Should have cue markers
        self.assertIn("#EXT-X-CUE-OUT", rewritten)
        self.assertIn("#EXT-X-CUE-IN", rewritten)
    
    def test_variant_with_preroll_resumes_live_segments(self):
        """
        Task 5.3: Pre-roll injection resumes live segments after ad block.
        
        After ad segments, the variant should resume live segment URIs.
        """
        rewritten, should_promote = build_variant_with_preroll(
            self.variant_playlist,
            self.session_id,
            self.mock_pod,
            "/storage/ads",
        )
        
        # Should have live segment URIs after ad block
        self.assertIn(f"/session/{self.session_id}/seg/live/video-240p0.ts", rewritten)
        self.assertIn(f"/session/{self.session_id}/seg/live/video-240p1.ts", rewritten)
    
    def test_variant_with_preroll_returns_promote_signal(self):
        """
        Task 5.3: Pre-roll injection signals that pod should be promoted to active.
        
        When build_variant_with_preroll is called with a pending pod,
        Then it returns (playlist, True) to indicate state promotion is needed
        """
        rewritten, should_promote = build_variant_with_preroll(
            self.variant_playlist,
            self.session_id,
            self.mock_pod,
            "/storage/ads",
        )
        
        self.assertTrue(should_promote)


if __name__ == "__main__":
    unittest.main()
