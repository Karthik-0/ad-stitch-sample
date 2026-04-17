from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Awaitable, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

import httpx

from config import PUBLIC_BASE_URL
from models import TrackingEvent


class VastClientError(Exception):
    pass


class WrapperDepthExceededError(VastClientError):
    pass


class VastParseError(VastClientError):
    pass


@dataclass
class ParsedAd:
    creative_id: str
    media_url: str
    duration_sec: float
    impression_urls: list[str]
    tracking_events: list[TrackingEvent]
    click_through_url: str | None = None


@dataclass
class AdBreakInfo:
    break_id: str
    time_offset: str
    tag_url: str


Fetcher = Callable[[str], Awaitable[str]]


def generate_correlator() -> str:
    return str(int(time.time() * 1000))


def expand_ad_tag_macros(url: str) -> str:
    """Expand a small set of common ad tag placeholders for server-side calls."""
    timestamp = str(int(time.time() * 1000))
    return (
        url.replace("[timestamp]", timestamp)
        .replace("[referrer_url]", PUBLIC_BASE_URL)
        .replace("[description_url]", PUBLIC_BASE_URL)
    )


def add_correlator(url: str, correlator: str | None = None) -> str:
    url = expand_ad_tag_macros(url)
    value = correlator or generate_correlator()
    split = urlsplit(url)
    query_items = parse_qsl(split.query, keep_blank_values=True)
    query_items = [item for item in query_items if item[0] != "correlator"]
    query_items.append(("correlator", value))
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query_items), split.fragment))


def parse_duration_to_seconds(duration_text: str) -> float:
    parts = duration_text.strip().split(":")
    if len(parts) != 3:
        raise VastParseError(f"invalid duration format: {duration_text}")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def normalize_url(url: str) -> str:
    return url.replace("[CACHEBUSTING]", str(random.randint(10000000, 99999999))).strip()


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _child_by_name(node: ET.Element, child_name: str) -> ET.Element | None:
    for child in list(node):
        if _local_name(child.tag) == child_name:
            return child
    return None


def _all_by_name(node: ET.Element, target_name: str) -> list[ET.Element]:
    return [item for item in node.iter() if _local_name(item.tag) == target_name]


def _text(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _select_media_file(linear: ET.Element) -> str:
    candidates: list[tuple[int, str]] = []
    for media in _all_by_name(linear, "MediaFile"):
        delivery = media.attrib.get("delivery", "").lower()
        media_type = media.attrib.get("type", "").lower()
        if delivery != "progressive" or media_type != "video/mp4":
            continue
        url = _text(media)
        if not url:
            continue
        bitrate = int(media.attrib.get("bitrate", "0") or "0")
        candidates.append((bitrate, url))

    if not candidates:
        raise VastParseError("no compatible progressive mp4 media file found")

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _parse_inline_ad(ad_node: ET.Element, inline_node: ET.Element, index: int) -> ParsedAd:
    creative_elem = _child_by_name(_child_by_name(inline_node, "Creatives") or ET.Element("empty"), "Creative")
    linear = _child_by_name(creative_elem or ET.Element("empty"), "Linear")
    if linear is None:
        raise VastParseError("inline ad missing Linear creative")

    media_url = _select_media_file(linear)
    duration_text = _text(_child_by_name(linear, "Duration"))
    duration_sec = parse_duration_to_seconds(duration_text)

    parsed_creative_id = ""
    if creative_elem is not None:
        parsed_creative_id = creative_elem.attrib.get("id", "")
    if not parsed_creative_id:
        parsed_creative_id = ad_node.attrib.get("id", "")
    if not parsed_creative_id:
        parsed_creative_id = f"ad-{index}"

    impression_urls: list[str] = []
    for impression in _all_by_name(inline_node, "Impression"):
        text = _text(impression)
        if text:
            impression_urls.append(normalize_url(text))

    tracking_events: list[TrackingEvent] = []
    for track in _all_by_name(linear, "Tracking"):
        event_name = track.attrib.get("event", "").strip()
        url = _text(track)
        if event_name and url:
            tracking_events.append(TrackingEvent(event=event_name, url=normalize_url(url)))

    click_through_node = _child_by_name(_child_by_name(linear, "VideoClicks") or ET.Element("empty"), "ClickThrough")
    click_through_url = _text(click_through_node) or None

    return ParsedAd(
        creative_id=parsed_creative_id,
        media_url=media_url,
        duration_sec=duration_sec,
        impression_urls=impression_urls,
        tracking_events=tracking_events,
        click_through_url=click_through_url,
    )


def parse_vast_xml(xml_text: str) -> tuple[list[ParsedAd], str | None]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise VastParseError("invalid VAST XML") from exc

    ads: list[ParsedAd] = []
    wrapper_url: str | None = None

    for index, ad_node in enumerate(_all_by_name(root, "Ad"), start=1):
        wrapper = _child_by_name(ad_node, "Wrapper")
        if wrapper is not None:
            wrapped_tag = _text(_child_by_name(wrapper, "VASTAdTagURI"))
            if wrapped_tag:
                wrapper_url = wrapped_tag
                continue

        inline = _child_by_name(ad_node, "InLine")
        if inline is None:
            continue
        ads.append(_parse_inline_ad(ad_node, inline, index))

    if ads:
        return ads, None
    if wrapper_url:
        return [], wrapper_url
    raise VastParseError("no inline ads or wrapper url found")


def parse_vmap_xml(xml_text: str) -> list[AdBreakInfo]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise VastParseError("invalid VMAP XML") from exc

    breaks: list[AdBreakInfo] = []
    for index, ad_break in enumerate(_all_by_name(root, "AdBreak"), start=1):
        break_id = ad_break.attrib.get("breakId", "").strip() or f"break-{index}"
        time_offset = ad_break.attrib.get("timeOffset", "start").strip() or "start"

        tag_uri = ""
        for candidate_name in ("VASTAdTagURI", "AdTagURI"):
            node = _child_by_name(ad_break, candidate_name)
            tag_uri = _text(node)
            if tag_uri:
                break
            for nested in _all_by_name(ad_break, candidate_name):
                tag_uri = _text(nested)
                if tag_uri:
                    break
            if tag_uri:
                break

        if not tag_uri:
            continue
        breaks.append(AdBreakInfo(break_id=break_id, time_offset=time_offset, tag_url=tag_uri))

    return breaks


async def _fetch_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.text


async def _fetch_vast_recursive(
    tag_url: str,
    depth: int,
    max_wrapper_depth: int,
    fetcher: Fetcher,
) -> list[ParsedAd]:
    if depth > max_wrapper_depth:
        raise WrapperDepthExceededError("VAST wrapper depth exceeded maximum")

    request_url = add_correlator(tag_url)
    xml_text = await fetcher(request_url)
    ads, wrapper_url = parse_vast_xml(xml_text)
    if ads:
        return ads
    if wrapper_url is None:
        raise VastParseError("wrapper response missing VASTAdTagURI")
    return await _fetch_vast_recursive(wrapper_url, depth + 1, max_wrapper_depth, fetcher)


async def fetch_vast(tag_url: str, max_wrapper_depth: int = 5) -> list[ParsedAd]:
    return await _fetch_vast_recursive(tag_url, depth=0, max_wrapper_depth=max_wrapper_depth, fetcher=_fetch_text)


async def fetch_vmap(tag_url: str) -> list[AdBreakInfo]:
    request_url = add_correlator(tag_url)
    xml_text = await _fetch_text(request_url)
    return parse_vmap_xml(xml_text)
