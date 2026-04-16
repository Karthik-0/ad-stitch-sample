from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import httpx

from config import ADS_DIR, AUDIO_CHANNELS, AUDIO_SAMPLE_RATE, FRAME_RATE, GOP_SIZE, RENDITIONS, SEGMENT_DURATION
from models import ConditionedAd, TrackingEvent
from vast_client import ParsedAd


class AdConditionerError(Exception):
    pass


def build_ffmpeg_command(input_path: Path, creative_dir: Path, rendition: dict[str, int | str]) -> list[str]:
    rendition_name = str(rendition["name"])
    width = int(rendition["width"])
    height = int(rendition["height"])
    video_bitrate = int(rendition["v_bitrate"])
    audio_bitrate = int(rendition["a_bitrate"])

    segment_pattern = str(creative_dir / f"{rendition_name}_%d.ts")
    playlist_path = str(creative_dir / f"{rendition_name}.m3u8")

    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"scale={width}:{height}",
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-level",
        "4.0",
        "-b:v",
        str(video_bitrate),
        "-maxrate",
        str(video_bitrate),
        "-bufsize",
        str(video_bitrate * 2),
        "-r",
        str(FRAME_RATE),
        "-g",
        str(GOP_SIZE),
        "-keyint_min",
        str(GOP_SIZE),
        "-sc_threshold",
        "0",
        "-c:a",
        "aac",
        "-b:a",
        str(audio_bitrate),
        "-ar",
        str(AUDIO_SAMPLE_RATE),
        "-ac",
        str(AUDIO_CHANNELS),
        "-f",
        "hls",
        "-hls_time",
        str(SEGMENT_DURATION),
        "-hls_playlist_type",
        "vod",
        "-hls_flags",
        "independent_segments",
        "-hls_segment_filename",
        segment_pattern,
        playlist_path,
    ]


def parse_hls_playlist(playlist_path: Path) -> list[tuple[str, float]]:
    if not playlist_path.exists():
        raise AdConditionerError(f"playlist missing: {playlist_path}")

    segments: list[tuple[str, float]] = []
    lines = [line.strip() for line in playlist_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    expected_duration: float | None = None
    for line in lines:
        if line.startswith("#EXTINF:"):
            duration_text = line.split(":", 1)[1].split(",", 1)[0]
            expected_duration = float(duration_text)
            continue
        if line.startswith("#"):
            continue
        if expected_duration is not None:
            segments.append((line, expected_duration))
            expected_duration = None

    if not segments:
        raise AdConditionerError(f"no segments parsed from {playlist_path}")

    return segments


async def _download_media(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        destination.write_bytes(response.content)
    return destination


def _expected_playlist_paths(creative_dir: Path) -> list[Path]:
    return [creative_dir / f"{rendition['name']}.m3u8" for rendition in RENDITIONS]


def _cache_ready(creative_dir: Path) -> bool:
    done_marker = creative_dir / ".done"
    if not done_marker.exists():
        return False

    try:
        for playlist in _expected_playlist_paths(creative_dir):
            parse_hls_playlist(playlist)
    except AdConditionerError:
        return False

    return True


async def _run_ffmpeg(command: list[str]) -> None:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise AdConditionerError(f"ffmpeg failed with code {process.returncode}: {stderr.decode('utf-8', errors='replace')}")


async def _transcode_rendition(input_path: Path, creative_dir: Path, rendition: dict[str, int | str]) -> tuple[str, list[tuple[str, float]]]:
    rendition_name = str(rendition["name"])
    command = build_ffmpeg_command(input_path=input_path, creative_dir=creative_dir, rendition=rendition)
    await _run_ffmpeg(command)
    playlist_path = creative_dir / f"{rendition_name}.m3u8"
    return rendition_name, parse_hls_playlist(playlist_path)


def _build_conditioned_ad(
    parsed_ad: ParsedAd,
    rendition_segments: dict[str, list[tuple[str, float]]],
) -> ConditionedAd:
    return ConditionedAd(
        creative_id=parsed_ad.creative_id,
        duration_sec=parsed_ad.duration_sec,
        renditions=rendition_segments,
        tracking=[TrackingEvent(event=event.event, url=event.url, fired=event.fired) for event in parsed_ad.tracking_events],
        impression_urls=list(parsed_ad.impression_urls),
    )


async def condition_ad(parsed_ad: ParsedAd) -> ConditionedAd:
    creative_dir = ADS_DIR / parsed_ad.creative_id
    creative_dir.mkdir(parents=True, exist_ok=True)

    if _cache_ready(creative_dir):
        cached_renditions = {
            str(rendition["name"]): parse_hls_playlist(creative_dir / f"{rendition['name']}.m3u8")
            for rendition in RENDITIONS
        }
        return _build_conditioned_ad(parsed_ad, cached_renditions)

    temp_media_path = Path(tempfile.gettempdir()) / f"{parsed_ad.creative_id}.mp4"
    done_marker = creative_dir / ".done"

    await _download_media(parsed_ad.media_url, temp_media_path)

    try:
        results = await asyncio.gather(
            *[_transcode_rendition(temp_media_path, creative_dir, rendition) for rendition in RENDITIONS]
        )
        rendition_map = {rendition_name: segments for rendition_name, segments in results}
        done_marker.write_text("ok\n", encoding="utf-8")
        return _build_conditioned_ad(parsed_ad, rendition_map)
    except Exception as exc:
        if done_marker.exists():
            done_marker.unlink()
        raise AdConditionerError(f"conditioning failed for creative {parsed_ad.creative_id}") from exc
    finally:
        if temp_media_path.exists():
            temp_media_path.unlink()


def clear_creative_cache(creative_id: str) -> None:
    creative_dir = ADS_DIR / creative_id
    if creative_dir.exists():
        shutil.rmtree(creative_dir)
