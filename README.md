# jarvis-cmd-youtube-music

> **Archived on 20261108 and no longer maintained.** Jarvis is using [Music Assistant](https://github.com/music-assistant) as its music integration point. Spotify and Pandora keep their own packages for power users, and Music Assistant covers every other service, so a package per service is not needed. Use [jarvis-cmd-music-assistant](https://github.com/alexberardi/jarvis-cmd-music-assistant) instead. The code here searched and resolved streams live, but was never heard on a node speaker, and it relied on unofficial libraries.

A [Jarvis](https://github.com/alexberardi/jarvis-server) Pantry package that plays music from YouTube Music through the node's speaker, with no account.

## What you can say

| You say                                        | Plays                                |
| ---------------------------------------------- | ------------------------------------ |
| "Play Hysteria by Muse on YouTube Music"       | The song                             |
| "Play the album Rumours from YouTube Music"    | The album                            |
| "Play Taylor Swift on YouTube Music"           | The artist (an exact name), shuffled |
| "Play my Chill Hits playlist on YouTube Music" | The playlist                         |
| "YouTube Music, play Discover Weekly"          | Best match                           |

The phrase must include "YouTube Music". These are fast paths, so the node runs them with no model, and each can be switched off
in the app's Inspect fast-paths screen. With [jarvis-cmd-music](https://github.com/opticon454/jarvis-cmd-music), "play
Korn" also works and uses your default music service.

## Requirements

- `mpv` on the node.
- A current `yt-dlp`, which this package installs with pip. YouTube changes often and old copies stop working (an April 2025 build failed in testing), so keep it updated.
- yt-dlp now wants a JavaScript runtime such as [deno](https://deno.com/) on the node; it warns when none is found.

## Settings

Entered in the Jarvis app; nothing is stored in this repository.

This package needs no settings.

## How it plays

The command finds the music, then starts `mpv` on the node with the stream addresses. A new play replaces the old one,
pauses the Spotify Connect receiver if it is running, and ends any other `mpv`, so two streams never share the speaker.
Audio goes to a connected Bluetooth speaker, else PulseAudio (so the agent can lower it while you talk), else the Pi
image's ALSA `output` alias. Long queues are limited to 50 tracks.

## Status

Verified live on 20261108: the real search, the real stream resolution with yt-dlp 2026.10.26, and mpv opening the result (audio output off). **Not yet heard through a node speaker.** ytmusicapi and yt-dlp are unofficial and YouTube's terms may not allow them.

## Tests

```bash
PYTHONPATH=/path/to/jarvis-command-sdk python3 -m pytest
```

The tests use fakes, so no node, account or network is needed.

## Licence

Apache-2.0. Not affiliated with YouTube Music. `mpv` is a separate program and is not included.
