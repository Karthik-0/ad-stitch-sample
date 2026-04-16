"""HLS manifest builder for session-aware playlist rewriting and live-edge ad injection."""

import re
from typing import Optional, Tuple

from models import AdPod


EXTINF_PATTERN = re.compile(r'^#EXTINF:([0-9.]+),')
MEDIA_SEQUENCE_PATTERN = re.compile(r'^#EXT-X-MEDIA-SEQUENCE:(\d+)$', re.MULTILINE)
VERSION_PATTERN = re.compile(r'^#EXT-X-VERSION:(\d+)$', re.MULTILINE)
TARGET_DURATION_PATTERN = re.compile(r'^#EXT-X-TARGETDURATION:(\d+)$', re.MULTILINE)

LIVE_WINDOW_SEGMENTS = 6


def build_master(live_master_playlist: str, session_id: str) -> str:
    lines = live_master_playlist.split('\n')
    output = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            output.append(line)
            continue
        if stripped and not stripped.startswith('#'):
            rendition = _extract_rendition_from_uri(stripped)
            if rendition:
                output.append(f'/session/{session_id}/{rendition}.m3u8')
            else:
                output.append(line)
            continue
        output.append(line)

    return '\n'.join(output)


def get_next_media_sequence(live_variant_playlist: str) -> int:
    parsed = _parse_variant_playlist(live_variant_playlist)
    return parsed['media_sequence'] + len(parsed['segment_blocks'])


def get_last_media_sequence(live_variant_playlist: str) -> int:
    return max(0, get_next_media_sequence(live_variant_playlist) - 1)


def build_variant_live_only(live_variant_playlist: str, session_id: str) -> str:
    parsed = _parse_variant_playlist(live_variant_playlist)
    live_segment_blocks, media_sequence = _select_live_window(parsed)
    return _render_variant_playlist(
        parsed=parsed,
        session_id=session_id,
        media_sequence=media_sequence,
        live_segment_blocks=live_segment_blocks,
    )


def build_variant_with_preroll(
    live_variant_playlist: str,
    session_id: str,
    pending_pod: AdPod,
    rendition: str,
    creative_dir: str,
    splice_at_sequence: Optional[int] = None,
) -> Tuple[str, bool]:
    del creative_dir

    parsed = _parse_variant_playlist(live_variant_playlist)
    live_segment_blocks, live_media_sequence = _select_live_window(
        parsed,
        start_sequence=splice_at_sequence,
    )
    ad_segments = pending_pod.ads[0].renditions.get(rendition, [])

    if splice_at_sequence is None:
        media_sequence = max(0, live_media_sequence - len(ad_segments))
    else:
        media_sequence = splice_at_sequence

    rewritten = _render_variant_playlist(
        parsed=parsed,
        session_id=session_id,
        media_sequence=media_sequence,
        live_segment_blocks=live_segment_blocks,
        ad_segments=ad_segments,
        rendition=rendition,
    )
    return rewritten, True


def _extract_rendition_from_uri(uri: str) -> Optional[str]:
    match = re.search(r'video-([a-z0-9]+)\.m3u8?', uri.lower())
    if match:
        return match.group(1)
    return None


def _parse_variant_playlist(live_variant_playlist: str) -> dict[str, object]:
    lines = live_variant_playlist.split('\n')
    header_lines: list[str] = []
    segment_blocks: list[list[str]] = []
    pending_block: list[str] = []
    in_segments = False

    for line in lines:
        stripped = line.strip()

        if not in_segments:
            if stripped.startswith('#EXTINF:') or (stripped and not stripped.startswith('#')):
                in_segments = True
                pending_block = [line]
            else:
                header_lines.append(line)
            continue

        if stripped.startswith('#EXT-X-ENDLIST'):
            continue

        pending_block.append(line)
        if stripped and not stripped.startswith('#'):
            segment_blocks.append(pending_block)
            pending_block = []

    version_match = VERSION_PATTERN.search(live_variant_playlist)
    target_duration_match = TARGET_DURATION_PATTERN.search(live_variant_playlist)
    media_sequence_match = MEDIA_SEQUENCE_PATTERN.search(live_variant_playlist)

    return {
        'header_lines': header_lines,
        'segment_blocks': segment_blocks,
        'version': int(version_match.group(1)) if version_match else 3,
        'target_duration': int(target_duration_match.group(1)) if target_duration_match else 10,
        'media_sequence': int(media_sequence_match.group(1)) if media_sequence_match else 0,
    }


def _select_live_window(
    parsed: dict[str, object],
    start_sequence: Optional[int] = None,
) -> tuple[list[list[str]], int]:
    segment_blocks = parsed['segment_blocks']
    media_sequence = int(parsed['media_sequence'])

    if not segment_blocks:
        return [], media_sequence

    if start_sequence is None:
        start_index = max(0, len(segment_blocks) - LIVE_WINDOW_SEGMENTS)
    else:
        start_index = max(0, start_sequence - media_sequence)
        if start_index >= len(segment_blocks):
            return [], start_sequence

    end_index = min(len(segment_blocks), start_index + LIVE_WINDOW_SEGMENTS)
    return segment_blocks[start_index:end_index], media_sequence + start_index


def _render_variant_playlist(
    parsed: dict[str, object],
    session_id: str,
    media_sequence: int,
    live_segment_blocks: list[list[str]],
    ad_segments: Optional[list[tuple[str, float]]] = None,
    rendition: Optional[str] = None,
) -> str:
    output = [
        '#EXTM3U',
        f'#EXT-X-VERSION:{parsed["version"]}',
        f'#EXT-X-TARGETDURATION:{_render_target_duration(parsed, ad_segments)}',
        f'#EXT-X-MEDIA-SEQUENCE:{media_sequence}',
    ]
    output.extend(_passthrough_header_lines(parsed['header_lines']))

    if ad_segments:
        output.append('#EXT-X-CUE-OUT:DURATION=' + str(sum(duration for _, duration in ad_segments)))
        output.append('#EXT-X-DISCONTINUITY')
        for ad_segment_index, (_, duration) in enumerate(ad_segments):
            output.append(f'#EXTINF:{duration},')
            output.append(f'/session/{session_id}/seg/ad/{rendition}/{ad_segment_index}')
        output.append('#EXT-X-DISCONTINUITY')
        output.append('#EXT-X-CUE-IN')

    for block in live_segment_blocks:
        output.extend(_rewrite_live_segment_block(block, session_id))

    return '\n'.join(line for line in output if line != '')


def _passthrough_header_lines(header_lines: list[str]) -> list[str]:
    passthrough = []
    for line in header_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == '#EXTM3U':
            continue
        if stripped.startswith('#EXT-X-VERSION'):
            continue
        if stripped.startswith('#EXT-X-TARGETDURATION'):
            continue
        if stripped.startswith('#EXT-X-MEDIA-SEQUENCE'):
            continue
        passthrough.append(line)
    return passthrough


def _rewrite_live_segment_block(block: list[str], session_id: str) -> list[str]:
    rewritten = []
    for line in block:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            rewritten.append(f'/session/{session_id}/seg/live/{stripped}')
        else:
            rewritten.append(line)
    return rewritten


def _render_target_duration(
    parsed: dict[str, object],
    ad_segments: Optional[list[tuple[str, float]]],
) -> int:
    live_target = int(parsed['target_duration'])
    if not ad_segments:
        return live_target
    ad_max = max((duration for _, duration in ad_segments), default=0.0)
    return max(live_target, int(ad_max) + 1)
