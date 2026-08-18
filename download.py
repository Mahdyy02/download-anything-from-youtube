#!/usr/bin/env python3
"""
ytb - a simple YouTube downloader CLI.

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

from pytubefix import YouTube
from tqdm import tqdm

video_bar = None
audio_bar = None


def make_bar(label, total):
    return tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc=label,
        leave=True,
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
    )


def on_progress(stream, chunk, bytes_remaining):
    global video_bar, audio_bar

    total = stream.filesize
    bar = video_bar if stream.type == "video" else audio_bar

    if bar is None:
        bar = make_bar("Video" if stream.type == "video" else "Audio", total)
        if stream.type == "video":
            video_bar = bar
        else:
            audio_bar = bar

    bar.n = total - bytes_remaining
    bar.refresh()


def notify(title, message):
    """Best-effort desktop notification. Silently does nothing if unavailable."""
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", title, message], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # fallback: terminal bell
        sys.stdout.write("\a")
        sys.stdout.flush()


def sanitize_filename(name, fallback):
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(char, '')
    name = name.strip()
    return name if name else fallback


def main():
    parser = argparse.ArgumentParser(
        prog="ytb",
        description="Download YouTube videos or audio from the command line."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o", "--audio-only",
        action="store_true",
        help="Download audio only (best available quality)"
    )
    parser.add_argument(
        "-d", "--output-dir",
        default=os.path.join(os.path.expanduser("~"), "Downloads"),
        help="Directory to save the file (default: ~/Downloads)"
    )
    args = parser.parse_args()

    output_dir = os.path.expanduser(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    if not shutil.which("ffmpeg") and not args.audio_only:
        print("⚠️  ffmpeg not found. Install it first, e.g.: sudo apt install ffmpeg")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Fetching video information...")
    print("=" * 60)

    yt = YouTube(args.url, on_progress_callback=on_progress)

    print(f"\n📹 Title: {yt.title}")
    print(f"👤 Author: {yt.author}")
    print(f"⏱️  Duration: {yt.length // 60}m {yt.length % 60}s")

    # AUDIO ONLY MODE
    if args.audio_only:
        print(f"\n🎵 Mode: Audio Only")
        print("-" * 60)

        audio_stream = (
            yt.streams
            .filter(adaptive=True, type="audio")
            .order_by("abr")
            .desc()
            .first()
        )

        if not audio_stream:
            print("❌ No audio stream found.")
            sys.exit(1)

        print(f"Quality: {audio_stream.abr}")
        print(f"Save location: {output_dir}\n")

        audio_file = audio_stream.download(output_path=output_dir)

        if audio_bar:
            audio_bar.close()

        print(f"\n✅ Audio download completed!")
        print(f"📂 Saved to: {audio_file}")
        print("=" * 60)
        notify("ytb", "Audio download completed")
        sys.exit(0)

    # VIDEO + AUDIO MODE (DEFAULT)
    print(f"\n🎬 Mode: Video + Audio")
    print("-" * 60)

    video_stream = (
        yt.streams
        .filter(adaptive=True, type="video", mime_type="video/webm")
        .order_by("resolution")
        .desc()
        .first()
    )

    audio_stream = (
        yt.streams
        .filter(adaptive=True, type="audio")
        .order_by("abr")
        .desc()
        .first()
    )

    if not video_stream or not audio_stream:
        print("❌ Could not find suitable streams.")
        sys.exit(1)

    print(f"Video resolution: {video_stream.resolution}")
    print(f"Audio quality: {audio_stream.abr}")
    print(f"Save location: {output_dir}\n")

    video_file = video_stream.download(filename="video_temp.mp4", output_path=output_dir)
    audio_file = audio_stream.download(filename="audio_temp.mp4", output_path=output_dir)

    if video_bar:
        video_bar.close()
    if audio_bar:
        audio_bar.close()

    safe_title = sanitize_filename(yt.title, yt.video_id)
    output_file = os.path.join(output_dir, f"{safe_title}.mp4")

    print("\n🔄 Merging audio and video...")

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", video_file,
            "-i", audio_file,
            "-c:v", "copy",
            "-c:a", "aac",
            output_file,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    os.remove(video_file)
    os.remove(audio_file)

    if result.returncode == 0:
        print("✅ Merge completed successfully!")
        print(f"\n📂 Saved to: {output_file}")
        print("=" * 60)
        notify("ytb", "Video download completed")
    else:
        print("❌ Error during merge. Check that ffmpeg is installed correctly.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
