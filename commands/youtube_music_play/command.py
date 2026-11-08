"""YouTubeMusicPlayCommand: "play <something> on YouTube Music" through this node's speaker (mpv)."""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

for _candidate in ("youtube_music_shared", "lib"):
    _lib_dir: str = str(Path.home() / ".jarvis" / "packages" / "youtube_music_play" / _candidate)
    if _lib_dir not in sys.path:
        sys.path.insert(0, _lib_dir)

try:
    from jarvis_log_client import JarvisLogger
except ImportError:
    import logging

    class JarvisLogger:  # noqa: E303
        def __init__(self, **kw: str) -> None:
            self._log = logging.getLogger(kw.get("service", __name__))

        def error(self, msg: str, **kw: object) -> None: self._log.error(msg)

from jarvis_command_sdk import (
    CommandExample,
    CommandResponse,
    FastPathPattern,
    IJarvisCommand,
    IJarvisSecret,
    JarvisPackage,
    JarvisParameter,
    JarvisSecret,
    JarvisStorage,
    RequestInformation,
)
from jarvis_command_sdk.command import PreRouteResult

from youtube_music_shared.music_common import AUTO, KINDS, PLAYER, ServiceError, fast_arguments, fast_regexes
from youtube_music_shared.youtube_music_service import YouTubeMusicService, ytdl_path

logger = JarvisLogger(service="youtube_music-play")
_PLAY_ON, _NAME_FIRST = fast_regexes(r"(?:you\s*tube\s+music|yt\s+music|youtube)")


class YouTubeMusicPlayCommand(IJarvisCommand):
    """Voice search and play on YouTube Music."""

    def __init__(self) -> None:
        self._storage = JarvisStorage("youtube_music_play")

    @property
    def command_name(self) -> str:
        return "youtube_music_play"

    @property
    def description(self) -> str:
        return (
            "Play a song, album, artist or playlist from YouTube Music. query is what to play, kind says what it is "
            "(leave empty unless the user says song, album, artist or playlist), artist narrows a song or album. "
            "Use when the user names YouTube Music: 'play ... on YouTube Music'."
        )

    @property
    def associated_service(self) -> Optional[str]:
        return "YouTube Music"

    @property
    def keywords(self) -> List[str]:
        return ["youtube music", "youtube", "play on youtube music", "play from youtube music", "song", "album", "playlist"]

    @property
    def parameters(self) -> List[JarvisParameter]:
        return [
            JarvisParameter("query", "string", required=True,
                            description="What to play: a song, album, artist or playlist name, without the service"),
            JarvisParameter("kind", "string", required=False, enum_values=KINDS,
                            description="track, album, artist or playlist. Leave empty when unsure."),
            JarvisParameter("artist", "string", required=False,
                            description="The artist, when the user named one for a song or album"),
        ]

    @property
    def fast_path_patterns(self) -> List[FastPathPattern]:
        return [
            FastPathPattern(id="youtube_music.play_on", description="Play something when you say 'on YouTube Music'",
                            example="Play Hysteria by Muse on YouTube Music", regex=_PLAY_ON, handler="_fast_play"),
            FastPathPattern(id="youtube_music.youtube_music_play", description="Play something when the phrase starts with 'YouTube Music'",
                            example="YouTube Music, play Discover Weekly", regex=_NAME_FIRST, handler="_fast_play"),
        ]

    def _fast_play(self, match: "re.Match[str]", voice_command: str) -> Optional[PreRouteResult]:
        args = fast_arguments(match.group("what"))
        return PreRouteResult(arguments=args) if args else None

    @property
    def required_secrets(self) -> List[IJarvisSecret]:
        return [
            # no settings: nothing to sign in to
        ]

    @property
    def required_packages(self) -> List[JarvisPackage]:
        return [JarvisPackage("ytmusicapi", ">=1.8.0"), JarvisPackage("yt-dlp", ">=2024.1.1")]

    @property
    def setup_guide(self) -> Optional[str]:
        return (
            '## YouTube Music\n'
            '\n'
            "No account or key is needed: it searches YouTube Music and plays the audio through this node's speaker. Both libraries are unofficial and can break when YouTube changes; keep them updated.\n"
            '\n'
            'The node needs `mpv` installed. Installing the `yt-dlp` package here is enough; the command points mpv at it.\n'
        )

    def generate_prompt_examples(self) -> List[CommandExample]:
        return [
            CommandExample("Play Hysteria by Muse on YouTube Music",
                           {"query": "Hysteria", "kind": "track", "artist": "Muse"}, is_primary=True),
            CommandExample("Play the album Black Holes and Revelations on YouTube Music",
                           {"query": "Black Holes and Revelations", "kind": "album"}),
            CommandExample("Play some Muse from YouTube Music", {"query": "Muse", "kind": "artist"}),
        ]

    def generate_adapter_examples(self) -> List[CommandExample]:
        rows = [
            ("Play Bohemian Rhapsody on YouTube Music", "Bohemian Rhapsody", "track", None),
            ("Play Thunderstruck by AC/DC from YouTube Music", "Thunderstruck", "track", "AC/DC"),
            ("Play the album Rumours on YouTube Music", "Rumours", "album", None),
            ("Play Abbey Road by The Beatles on YouTube Music", "Abbey Road", "album", "The Beatles"),
            ("Play Taylor Swift on YouTube Music", "Taylor Swift", "artist", None),
            ("Play my Chill Hits playlist on YouTube Music", "Chill Hits", "playlist", None),
            ("YouTube Music, play Running Up That Hill", "Running Up That Hill", "track", None),
        ]
        out = []
        for text, query, kind, artist in rows:
            params = {"query": query, "kind": kind}
            if artist:
                params["artist"] = artist
            out.append(CommandExample(text, params))
        return out

    def _service(self) -> YouTubeMusicService:
        from ytmusicapi import YTMusic

        return YouTubeMusicService(YTMusic(), ytdl_path())

    def run(self, request_info: RequestInformation, **kwargs: Any) -> CommandResponse:
        query = str(kwargs.get("query") or "").strip()
        if not query:
            return CommandResponse.error_response(error_details="What would you like me to play?",
                                                  context_data={"error": "missing_query"})
        kind = str(kwargs.get("kind") or AUTO).lower()
        try:
            item = self._service().find(query, kind, kwargs.get("artist"))
            PLAYER.play(item)
        except ServiceError as exc:
            return CommandResponse.error_response(error_details=str(exc), context_data={"error": "service_error"})
        except Exception as exc:  # noqa: BLE001 - never raise into the voice pipeline
            logger.error("YouTube Music play failed", error=str(exc))
            return CommandResponse.error_response(error_details="YouTube Music didn't respond. Try again in a moment.",
                                                  context_data={"error": "unexpected", "detail": str(exc)})
        return CommandResponse.success_response(
            context_data={"message": f"Playing {item.spoken()}.", "kind": item.kind}, wait_for_input=False)
