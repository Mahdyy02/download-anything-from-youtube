#!/usr/bin/env python3
"""
ytb - a simple YouTube downloader CLI, backed by yt-dlp.

Usage:
    ytb <youtube_url>
    ytb <youtube_url> -o | --audio-only
    ytb <youtube_url> -d ~/Videos
"""

import argparse
import os
import shutil
import subprocess
import sys

# YouTube requires a PO token to serve adaptive (separate video/audio, HD+)
# formats to most clients now. "mweb" exposes the full quality ladder once a
# PO token provider is available (see bgutil-ytdlp-pot-provider in the venv
# plus ~/bgutil-ytdlp-pot-provider, which supplies tokens via a deno script
# with no server needed).
PLAYER_CLIENTS = "mweb"
MAX_HEIGHT = 1080


def find_yt_dlp():
    """Look for yt-dlp next to the current Python interpreter (venv) first,
    then fall back to whatever is on PATH."""
    venv_candidate = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
    if os.path.isfile(venv_candidate) and os.access(venv_candidate, os.X_OK):
        return venv_candidate
    return shutil.which("yt-dlp")


def notify(title, message):
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", title, message], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        sys.stdout.write("\a")
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(
        prog="ytb",
        description="Download YouTube videos or audio from the command line (powered by yt-dlp)."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o", "--audio-only",
        action="store_true",
        help="Download audio only (best available quality, saved as m4a)"
    )
    parser.add_argument(
        "-d", "--output-dir",
        default=os.path.join(os.path.expanduser("~"), "Downloads"),
        help="Directory to save the file (default: ~/Downloads)"
    )
    args = parser.parse_args()

    yt_dlp_path = find_yt_dlp()
    if not yt_dlp_path:
        print("yt-dlp not found. Install it first, e.g.: pip install --user -U yt-dlp")
        sys.exit(1)

    output_dir = os.path.expanduser(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    out_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    if args.audio_only:
        cmd = [
            yt_dlp_path,
            "--extractor-args", f"youtube:player_client={PLAYER_CLIENTS}",
            "-x", "--audio-format", "m4a",
            "-o", out_template,
            "--no-playlist",
            args.url,
        ]
    else:
        cmd = [
            yt_dlp_path,
            "--extractor-args", f"youtube:player_client={PLAYER_CLIENTS}",
            "-f", f"bv*[height<={MAX_HEIGHT}]+ba/b[height<={MAX_HEIGHT}]",
            "--merge-output-format", "mp4",
            "-o", out_template,
            "--no-playlist",
            args.url,
        ]

    print("\n" + "=" * 60)
    print("Downloading with yt-dlp...")
    print("=" * 60 + "\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print(f"Download completed! Saved to: {output_dir}")
        print("=" * 60)
        notify("ytb", "Download completed")
    else:
        print("\nDownload failed. See yt-dlp output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
