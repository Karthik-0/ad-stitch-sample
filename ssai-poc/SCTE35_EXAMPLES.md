# Sample HLS manifests with SCTE-35 cues for testing

## Live Variant Playlist with SCTE-35 Splice Points

```m3u8
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:670

#EXTINF:6.0,
segment-670.ts
#EXTINF:6.0,
segment-671.ts
#EXTINF:6.0,
segment-672.ts
#EXT-X-CUE-OUT:30.0
#EXT-OATCLS-SCTE35:/DAAA7QA=
#EXTINF:6.0,
segment-673.ts
#EXTINF:6.0,
segment-674.ts
#EXTINF:6.0,
segment-675.ts
#EXTINF:6.0,
segment-676.ts
#EXTINF:6.0,
segment-677.ts
#EXT-X-CUE-IN
#EXTINF:6.0,
segment-678.ts
```

### Expected Behavior:
1. Player polls manifest and fetches segments 670-672 (live-only)
2. SCTE-35 detector encounters `#EXT-X-CUE-OUT:30.0` at segment 673
3. Auto-triggers mid-roll with 30-second duration at sequence 673
4. Player transitions through ad break (673-677), then resumes live at 678
5. Beacon fires at quartile points during ad playback

## Multiple Breaks in Single Manifest

```m3u8
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100

#EXTINF:6.0,
segment-100.ts
#EXT-X-CUE-OUT:30.0
#EXTINF:6.0,
segment-101.ts
...
#EXT-X-CUE-IN
#EXTINF:6.0,
segment-106.ts
#EXTINF:6.0,
segment-107.ts
#EXT-X-CUE-OUT:45.0
#EXTINF:6.0,
segment-108.ts
...
```

### Expected Behavior:
- First CUE-OUT at segment 101 → auto-trigger 30s ad break
- After 5 segments, CUE-IN marks end of first break
- Second CUE-OUT at segment 108 → auto-trigger 45s ad break (if not already processing an ad)
