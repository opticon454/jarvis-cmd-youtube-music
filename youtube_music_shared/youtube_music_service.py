"""Find music on YouTube Music (no login) and give mpv watch URLs, which mpv opens through yt-dlp.

ytmusicapi does the catalogue search; yt-dlp (run by mpv) resolves the audio. Both are unofficial.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any, Optional

from youtube_music_shared.music_common import AUTO, KINDS, MAX_ITEMS, Resolved, ServiceError, pick

WATCH = "https://music.youtube.com/watch?v="
_FILTERS = {"track": "songs", "artist": "artists", "album": "albums", "playlist": "playlists"}


def ytdl_path() -> Optional[str]:
    """The yt-dlp this package installed (beside the node's Python) wins over one on PATH, which is often months old
    and stops working when YouTube changes. mpv only looks on PATH itself, so it is named explicitly."""
    beside = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
    return beside if os.path.exists(beside) else shutil.which("yt-dlp")


class YouTubeMusicService:
    def __init__(self, client: Any, ytdl: Optional[str] = None) -> None:
        self._yt = client  # a ytmusicapi.YTMusic
        self._ytdl = ytdl

    def _search(self, query: str, kind: str) -> list[dict]:
        try:
            rows = self._yt.search(query, filter=_FILTERS[kind], limit=5, ignore_spelling=True) or []
        except Exception as exc:  # noqa: BLE001 - network and parsing errors
            raise ServiceError("YouTube Music didn't answer that. Try again in a moment.") from exc
        out = []
        for r in rows:
            if kind == "track" and r.get("videoId"):
                out.append({"name": r["title"], "id": r["videoId"], "by": _artists(r)})
            elif kind == "artist" and r.get("browseId"):
                out.append({"name": r.get("artist", ""), "id": r["browseId"], "by": ""})
            elif kind == "album" and r.get("browseId"):
                out.append({"name": r["title"], "id": r["browseId"], "by": _artists(r)})
            elif kind == "playlist" and r.get("browseId"):
                out.append({"name": r["title"], "id": r["browseId"], "by": ""})
        return out

    def find(self, query: str, kind: str = AUTO, artist: Optional[str] = None) -> Resolved:
        kind = kind if kind in KINDS else AUTO
        text = f"{query} {artist}" if artist else query
        found = {k: self._search(text if k in ("track", "album") else query, k) for k in (KINDS if kind == AUTO else [kind])}
        hit = pick(found, query, kind)
        if hit is None:
            raise ServiceError(f"I couldn't find {query} on YouTube Music.")
        k, item = hit
        ids = self._video_ids(k, item)
        if not ids:
            raise ServiceError(f"{item['name']} has nothing playable on YouTube Music.")
        args = ["--ytdl-format=bestaudio"]
        if self._ytdl:
            args.append(f"--script-opts=ytdl_hook-ytdl_path={self._ytdl}")
        return Resolved(k, item["name"], item["by"], [WATCH + i for i in ids], mpv_args=args, shuffle=k == "artist")

    def _video_ids(self, kind: str, item: dict) -> list[str]:
        try:
            if kind == "track":
                return [item["id"]]
            if kind == "album":
                tracks = self._yt.get_album(item["id"]).get("tracks") or []
            elif kind == "artist":
                songs = self._yt.get_artist(item["id"]).get("songs") or {}
                tracks = songs.get("results") or []
                if songs.get("browseId"):  # the full list; the page only shows the first few
                    tracks = self._yt.get_playlist(songs["browseId"], limit=MAX_ITEMS).get("tracks") or tracks
            else:
                tracks = self._yt.get_playlist(item["id"], limit=MAX_ITEMS).get("tracks") or []
        except Exception as exc:  # noqa: BLE001
            raise ServiceError("YouTube Music didn't answer that. Try again in a moment.") from exc
        return [t["videoId"] for t in tracks if t.get("videoId")][:MAX_ITEMS]  # the library's limit is not a hard cap


def _artists(row: dict) -> str:
    return ", ".join(a["name"] for a in (row.get("artists") or [])[:2] if a.get("name"))
