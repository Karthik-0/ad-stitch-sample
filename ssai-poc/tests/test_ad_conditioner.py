import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import ad_conditioner
from models import TrackingEvent
from vast_client import ParsedAd


class AdConditionerTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="ad-conditioner-tests-"))
        self.single_rendition = [
            {
                "name": "240p",
                "width": 426,
                "height": 240,
                "v_bitrate": 192000,
                "a_bitrate": 72000,
            }
        ]

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            for child in sorted(self.temp_dir.rglob("*"), reverse=True):
                if child.is_file() or child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            self.temp_dir.rmdir()

    def _parsed_ad(self) -> ParsedAd:
        return ParsedAd(
            creative_id="creative-1",
            media_url="https://cdn.example.com/ad.mp4",
            duration_sec=30.0,
            impression_urls=["https://tracker.example.com/imp"],
            tracking_events=[TrackingEvent(event="start", url="https://tracker.example.com/start")],
        )

    def test_build_ffmpeg_command_contains_required_flags(self) -> None:
        command = ad_conditioner.build_ffmpeg_command(
            input_path=Path("/tmp/input.mp4"),
            creative_dir=Path("/tmp/creative"),
            rendition=self.single_rendition[0],
        )
        joined = " ".join(command)
        for required in ["-r 24", "-g 48", "-keyint_min 48", "-sc_threshold 0", "-ar 44100", "-ac 2", "-profile:v main", "-level 4.0"]:
            self.assertIn(required, joined)

    def test_parse_hls_playlist_returns_ordered_segments(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "ad_playlist_sample.m3u8"
        segments = ad_conditioner.parse_hls_playlist(fixture)
        self.assertEqual(segments, [("240p_0.ts", 6.0), ("240p_1.ts", 6.0)])

    async def test_cache_hit_bypasses_transcoding(self) -> None:
        parsed_ad = self._parsed_ad()
        creative_dir = self.temp_dir / parsed_ad.creative_id
        creative_dir.mkdir(parents=True, exist_ok=True)
        (creative_dir / ".done").write_text("ok\n", encoding="utf-8")
        (creative_dir / "240p.m3u8").write_text(
            "#EXTM3U\n#EXTINF:6.0,\n240p_0.ts\n",
            encoding="utf-8",
        )

        with patch.object(ad_conditioner, "ADS_DIR", self.temp_dir), patch.object(ad_conditioner, "RENDITIONS", self.single_rendition), patch.object(ad_conditioner, "_run_ffmpeg", new=AsyncMock(side_effect=AssertionError("ffmpeg should not run"))):
            result = await ad_conditioner.condition_ad(parsed_ad)

        self.assertIn("240p", result.renditions)
        self.assertEqual(result.renditions["240p"][0][0], "240p_0.ts")

    async def test_cache_miss_runs_transcode_and_creates_done_marker(self) -> None:
        parsed_ad = self._parsed_ad()
        download_file = self.temp_dir / "download.mp4"
        download_file.write_bytes(b"mp4")

        async def fake_download(_: str, destination: Path) -> Path:
            destination.write_bytes(download_file.read_bytes())
            return destination

        async def fake_run(command: list[str]) -> None:
            playlist_path = Path(command[-1])
            segment_pattern = Path(command[command.index("-hls_segment_filename") + 1])
            segment_file = segment_pattern.name.replace("%d", "0")
            (playlist_path.parent / segment_file).write_bytes(b"ts")
            playlist_path.write_text(f"#EXTM3U\n#EXTINF:6.0,\n{segment_file}\n", encoding="utf-8")

        with patch.object(ad_conditioner, "ADS_DIR", self.temp_dir), patch.object(ad_conditioner, "RENDITIONS", self.single_rendition), patch.object(ad_conditioner, "_download_media", new=fake_download), patch.object(ad_conditioner, "_run_ffmpeg", new=fake_run):
            result = await ad_conditioner.condition_ad(parsed_ad)

        done_marker = self.temp_dir / parsed_ad.creative_id / ".done"
        self.assertTrue(done_marker.exists())
        self.assertIn("240p", result.renditions)

    async def test_transcode_failure_keeps_done_marker_absent(self) -> None:
        parsed_ad = self._parsed_ad()

        async def fake_download(_: str, destination: Path) -> Path:
            destination.write_bytes(b"mp4")
            return destination

        async def fake_run(_: list[str]) -> None:
            raise ad_conditioner.AdConditionerError("ffmpeg failed")

        with patch.object(ad_conditioner, "ADS_DIR", self.temp_dir), patch.object(ad_conditioner, "RENDITIONS", self.single_rendition), patch.object(ad_conditioner, "_download_media", new=fake_download), patch.object(ad_conditioner, "_run_ffmpeg", new=fake_run):
            with self.assertRaises(ad_conditioner.AdConditionerError):
                await ad_conditioner.condition_ad(parsed_ad)

        done_marker = self.temp_dir / parsed_ad.creative_id / ".done"
        self.assertFalse(done_marker.exists())


if __name__ == "__main__":
    unittest.main()
