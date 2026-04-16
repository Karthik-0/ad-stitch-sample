"""Unit tests for SCTE-35 cue detection and parsing."""

import unittest
from scte35_parser import (
    parse_cue_out,
    parse_cue_in,
    parse_scte35_payload,
    detect_scte35_cues,
    Scte35Cue,
)


class TestScte35Parser(unittest.TestCase):
    """Test SCTE-35 tag parsing utilities."""

    def test_parse_cue_out_with_integer(self):
        """Parse #EXT-X-CUE-OUT:30"""
        result = parse_cue_out("#EXT-X-CUE-OUT:30")
        self.assertEqual(result, 30.0)

    def test_parse_cue_out_with_float(self):
        """Parse #EXT-X-CUE-OUT:30.5"""
        result = parse_cue_out("#EXT-X-CUE-OUT:30.5")
        self.assertEqual(result, 30.5)

    def test_parse_cue_out_with_whitespace(self):
        """Parse with leading/trailing whitespace"""
        result = parse_cue_out("  #EXT-X-CUE-OUT:60  ")
        self.assertEqual(result, 60.0)

    def test_parse_cue_out_invalid(self):
        """Return None for invalid tags"""
        self.assertIsNone(parse_cue_out("#EXT-X-CUE-OUT:abc"))
        self.assertIsNone(parse_cue_out("#EXT-X-CUE-IN"))
        self.assertIsNone(parse_cue_out("segment.ts"))

    def test_parse_cue_in(self):
        """Detect #EXT-X-CUE-IN"""
        self.assertTrue(parse_cue_in("#EXT-X-CUE-IN"))
        self.assertTrue(parse_cue_in("  #EXT-X-CUE-IN  "))

    def test_parse_cue_in_invalid(self):
        """Return False for non-CUE-IN lines"""
        self.assertFalse(parse_cue_in("#EXT-X-CUE-OUT:30"))
        self.assertFalse(parse_cue_in("segment.ts"))

    def test_parse_scte35_payload_oatcls(self):
        """Parse #EXT-OATCLS-SCTE35:/DAAA..."""
        result = parse_scte35_payload("#EXT-OATCLS-SCTE35:/DAAA7QA=")
        self.assertEqual(result, "/DAAA7QA=")

    def test_parse_scte35_payload_with_x_prefix(self):
        """Parse #EXT-X-OATCLS-SCTE35:/DAAA..."""
        result = parse_scte35_payload("#EXT-X-OATCLS-SCTE35:/DAAA7QA=")
        self.assertEqual(result, "/DAAA7QA=")

    def test_parse_scte35_payload_invalid(self):
        """Return None for invalid payload tags"""
        self.assertIsNone(parse_scte35_payload("#EXT-X-CUE-OUT:30"))
        self.assertIsNone(parse_scte35_payload("segment.ts"))


class TestScte35CueDetection(unittest.TestCase):
    """Test SCTE-35 cue detection from manifests."""

    def test_detect_single_cue_out(self):
        """Detect a single CUE-OUT in manifest"""
        manifest = """\
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100

#EXTINF:6.0
segment-100.ts
#EXTINF:6.0
segment-101.ts
#EXT-X-CUE-OUT:30
#EXTINF:6.0
segment-102.ts
"""
        cues = detect_scte35_cues(manifest, 100)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].duration_sec, 30.0)
        self.assertIn("cue-seq", cues[0].cue_id)

    def test_detect_multiple_cues(self):
        """Detect multiple CUE-OUT events"""
        manifest = """\
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:200

#EXTINF:6.0
segment-200.ts
#EXT-X-CUE-OUT:30
#EXTINF:6.0
segment-201.ts
#EXT-X-CUE-IN
#EXTINF:6.0
segment-202.ts
#EXT-X-CUE-OUT:45
#EXTINF:6.0
segment-203.ts
"""
        cues = detect_scte35_cues(manifest, 200)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].duration_sec, 30.0)
        self.assertEqual(cues[1].duration_sec, 45.0)

    def test_filter_processed_cues(self):
        """Skip cues already processed"""
        manifest = """\
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:100

#EXTINF:6.0
segment-100.ts
#EXT-X-CUE-OUT:30
#EXTINF:6.0
segment-101.ts
"""
        cues1 = detect_scte35_cues(manifest, 100, processed_cue_ids=[])
        self.assertEqual(len(cues1), 1)
        cue_id = cues1[0].cue_id

        # Second call with same cue ID in processed list should return empty
        cues2 = detect_scte35_cues(manifest, 100, processed_cue_ids=[cue_id])
        self.assertEqual(len(cues2), 0)

    def test_cue_start_sequence_calculation(self):
        """Verify cue start_sequence is correctly calculated"""
        manifest = """\
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:500

#EXTINF:6.0
segment-500.ts
#EXTINF:6.0
segment-501.ts
#EXTINF:6.0
segment-502.ts
#EXT-X-CUE-OUT:30
#EXTINF:6.0
segment-503.ts
"""
        cues = detect_scte35_cues(manifest, 500)
        self.assertEqual(len(cues), 1)
        # Cue-out is on the 4th segment (index 3), so sequence = 500 + 3
        self.assertEqual(cues[0].start_sequence, 503)

    def test_scte35_payload_capture(self):
        """Capture SCTE-35 binary payload if present"""
        manifest = """\
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:100

#EXTINF:6.0
segment-100.ts
#EXT-OATCLS-SCTE35:/DAAA7QA=
#EXT-X-CUE-OUT:30
#EXTINF:6.0
segment-101.ts
"""
        cues = detect_scte35_cues(manifest, 100)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].payload, "/DAAA7QA=")

    def test_no_cues_in_live_manifest(self):
        """Return empty list if no cues detected"""
        manifest = """\
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100

#EXTINF:6.0
segment-100.ts
#EXTINF:6.0
segment-101.ts
#EXTINF:6.0
segment-102.ts
"""
        cues = detect_scte35_cues(manifest, 100)
        self.assertEqual(len(cues), 0)

    def test_cue_state_tracking(self):
        """Verify state alternates between out and in"""
        manifest = """\
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:100

#EXTINF:6.0
segment-100.ts
#EXT-X-CUE-OUT:30
#EXTINF:6.0
segment-101.ts
#EXT-X-CUE-IN
#EXTINF:6.0
segment-102.ts
"""
        cues = detect_scte35_cues(manifest, 100)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].state, "out")


if __name__ == "__main__":
    unittest.main()
