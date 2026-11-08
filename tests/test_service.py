import pytest

from youtube_music_shared.music_common import ServiceError
from youtube_music_shared.youtube_music_service import WATCH, YouTubeMusicService, ytdl_path


class YT:
    """Shaped like ytmusicapi.YTMusic's results (checked against the live library)."""

    def __init__(self, **by_filter):
        self.by_filter, self.calls, self.fail = by_filter, [], False

    def search(self, query, filter=None, limit=None, ignore_spelling=False):
        if self.fail:
            raise RuntimeError("blocked")
        self.calls.append((query, filter))
        return self.by_filter.get(filter, [])

    def get_album(self, browse_id):
        return {"tracks": [{"videoId": "t1"}, {"videoId": None}, {"videoId": "t2"}]}

    def get_artist(self, channel_id):
        return {"songs": {"browseId": "VLsongs", "results": [{"videoId": "r1"}]}}

    def get_playlist(self, playlist_id, limit=None):
        return {"tracks": [{"videoId": f"{playlist_id}-1"}, {"videoId": f"{playlist_id}-2"}]}


SONG = {"videoId": "v1", "title": "Freak On a Leash", "artists": [{"name": "Korn", "id": "x"}]}


def test_track_search_includes_the_artist_and_gives_a_watch_url_for_mpv():
    yt = YT(songs=[SONG])
    r = YouTubeMusicService(yt, "/venv/bin/yt-dlp").find("Freak on a Leash", "track", "Korn")
    assert yt.calls == [("Freak on a Leash Korn", "songs")]
    assert r.urls == [WATCH + "v1"] and r.spoken() == "Freak On a Leash by Korn"
    assert "--ytdl-format=bestaudio" in r.mpv_args and "--script-opts=ytdl_hook-ytdl_path=/venv/bin/yt-dlp" in r.mpv_args


def test_auto_picks_an_exact_artist_and_uses_the_full_songs_playlist_shuffled():
    yt = YT(artists=[{"browseId": "UC1", "artist": "Korn"}], songs=[SONG])
    r = YouTubeMusicService(yt).find("korn")
    assert r.kind == "artist" and r.shuffle and r.urls == [WATCH + "VLsongs-1", WATCH + "VLsongs-2"]
    assert not any("ytdl_path" in a for a in r.mpv_args)


def test_albums_skip_unavailable_tracks_and_playlists_expand():
    yt = YT(albums=[{"browseId": "MPRE1", "title": "Issues", "artists": [{"name": "Korn"}]}],
            playlists=[{"browseId": "VLPL1", "title": "Korn Greatest Hits"}])
    s = YouTubeMusicService(yt)
    assert s.find("Issues", "album").urls == [WATCH + "t1", WATCH + "t2"]
    assert s.find("Korn Greatest Hits", "playlist").urls == [WATCH + "VLPL1-1", WATCH + "VLPL1-2"]


def test_rows_without_ids_are_ignored_and_nothing_found_is_spoken():
    with pytest.raises(ServiceError, match="couldn't find Nope on YouTube Music"):
        YouTubeMusicService(YT(songs=[{"title": "no id", "artists": []}])).find("Nope", "track")


def test_library_errors_are_spoken():
    yt = YT()
    yt.fail = True
    with pytest.raises(ServiceError, match="didn't answer"):
        YouTubeMusicService(yt).find("x")


def test_ytdl_path_prefers_the_copy_installed_with_the_package(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/yt-dlp")
    (tmp_path / "python").write_text("")
    monkeypatch.setattr("sys.executable", str(tmp_path / "python"))
    assert ytdl_path() == "/usr/bin/yt-dlp"  # nothing installed beside python: fall back to PATH
    (tmp_path / "yt-dlp").write_text("")
    assert ytdl_path() == str(tmp_path / "yt-dlp")
    monkeypatch.setattr("shutil.which", lambda n: None)
    (tmp_path / "yt-dlp").unlink()
    assert ytdl_path() is None


def test_a_long_playlist_is_capped_even_if_the_library_returns_more():
    from youtube_music_shared.music_common import MAX_ITEMS

    class Big(YT):
        def get_playlist(self, playlist_id, limit=None):
            return {"tracks": [{"videoId": f"v{i}"} for i in range(MAX_ITEMS * 3)]}

    r = YouTubeMusicService(Big(playlists=[{"browseId": "VL1", "title": "Big"}])).find("Big", "playlist")
    assert len(r.urls) == MAX_ITEMS
