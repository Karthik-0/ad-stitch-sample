import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LIVE_DIR = Path(os.getenv("LIVE_DIR", str(BASE_DIR / "storage" / "live")))
ADS_DIR = Path(os.getenv("ADS_DIR", str(BASE_DIR / "storage" / "ads")))
PUBLIC_BASE_URL = "http://localhost:8080"

RTMP_URL = "rtmp://localhost:1935/live/livestream"

RENDITIONS = [
    {
        "name": "240p",
        "width": 426,
        "height": 240,
        "v_bitrate": 192000,
        "a_bitrate": 72000,
    },
    {
        "name": "480p",
        "width": 854,
        "height": 480,
        "v_bitrate": 500000,
        "a_bitrate": 128000,
    },
    {
        "name": "720p",
        "width": 1280,
        "height": 720,
        "v_bitrate": 1000000,
        "a_bitrate": 128000,
    },
]

FRAME_RATE = 24
GOP_SIZE = 48
SEGMENT_DURATION = 6
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2

VAST_TAG_SINGLE_LINEAR = (
    "https://pubads.g.doubleclick.net/gampad/ads?"
    "iu=/21775744923/external/single_ad_samples&sz=640x480"
    "&cust_params=sample_ct%3Dlinear&ciu_szs=300x250%2C728x90"
    "&gdfp_req=1&output=vast&unviewed_position_start=1&env=vp&impl=s&correlator="
)
VAST_TAG_VMAP_POD = (
    "https://pubads.g.doubleclick.net/gampad/ads?"
    "iu=/21775744923/external/vmap_ad_samples&sz=640x480"
    "&cust_params=sample_ar%3Dpremidpostpod&ciu_szs=300x250%2C728x90"
    "&gdfp_req=1&ad_rule=1&output=vmap&unviewed_position_start=1&env=vp&impl=s"
    "&cmsid=496&vid=short_onecue&correlator="
)

ACTIVE_VAST_TAG = VAST_TAG_SINGLE_LINEAR
SESSION_TTL_SECONDS = 3600
CLEANUP_INTERVAL_SECONDS = 300
