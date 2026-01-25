import sys
import os
import subprocess
from pytubefix import YouTube
from tqdm import tqdm
import winsound

# Get Downloads folder path
DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

if len(sys.argv) < 2:
    print("=" * 60)
    print("YouTube Downloader")
    print("=" * 60)
    print("\nUsage:")
    print("  python download.py <youtube_url>")
    print("  python download.py <youtube_url> -o | --audio_only")
    print("\nExamples:")
    print("  python download.py https://youtube.com/watch?v=...")
    print("  python download.py https://youtube.com/watch?v=... -o")
    print("=" * 60)
    sys.exit(1)

url = sys.argv[1]
audio_only = "-o" in sys.argv or "--audio_only" in sys.argv

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


print("\n" + "=" * 60)
print("Fetching video information...")
print("=" * 60)

yt = YouTube(url, on_progress_callback=on_progress)

print(f"\n📹 Title: {yt.title}")
print(f"👤 Author: {yt.author}")
print(f"⏱️  Duration: {yt.length // 60}m {yt.length % 60}s")

# AUDIO ONLY MODE
if audio_only:
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
    print(f"Save location: {DOWNLOADS_FOLDER}\n")

    audio_file = audio_stream.download(output_path=DOWNLOADS_FOLDER)

    if audio_bar:
        audio_bar.close()

    print(f"\n✅ Audio download completed!")
    print(f"📂 Saved to: {audio_file}")
    print("=" * 60)
    winsound.MessageBeep(winsound.MB_ICONASTERISK)
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
print(f"Save location: {DOWNLOADS_FOLDER}\n")

video_file = video_stream.download(filename="video_temp.mp4", output_path=DOWNLOADS_FOLDER)
audio_file = audio_stream.download(filename="audio_temp.mp4", output_path=DOWNLOADS_FOLDER)

if video_bar:
    video_bar.close()
if audio_bar:
    audio_bar.close()

# Clean filename - remove all problematic characters
safe_title = yt.title
# Remove characters that are invalid in Windows filenames
for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
    safe_title = safe_title.replace(char, '')
# Remove or replace other problematic characters
safe_title = safe_title.strip()
# If title is empty or only contains problematic chars, use video ID
if not safe_title:
    safe_title = yt.video_id
output_file = os.path.join(DOWNLOADS_FOLDER, f"{safe_title}.mp4")

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

# Clean up temporary files
os.remove(video_file)
os.remove(audio_file)

if result.returncode == 0:
    print("✅ Merge completed successfully!")
    print(f"\n📂 Saved to: {output_file}")
    print("=" * 60)
    winsound.MessageBeep(winsound.MB_ICONASTERISK)
else:
    print("❌ Error during merge. FFmpeg may not be installed.")
    print("=" * 60)
    sys.exit(1)