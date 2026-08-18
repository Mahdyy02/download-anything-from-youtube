# ytb - YouTube Downloader

A simple command-line tool to download YouTube videos (up to 1080p) or
audio-only files, using [yt-dlp](https://github.com/yt-dlp/yt-dlp) under
the hood.

You type `ytb <youtube-url>` in your terminal, and it saves the video (or
audio) to your Downloads folder.

## Why this is more than "pip install yt-dlp"

YouTube now blocks most download tools unless they present a special
"PO token" (proof-of-origin token). Without it, YouTube either refuses the
download outright (`HTTP Error 403: Forbidden`) or only allows an old,
low-quality 360p stream. To get proper 1080p downloads working, this setup
also installs a small token-generating helper
(`bgutil-ytdlp-pot-provider`) that runs locally on your machine — no
account login, no cloud service, nothing sent anywhere except to YouTube
itself.

This README walks through the entire setup, step by step, exactly as it
was done.

---

## 1. Requirements

Install these system packages first if you don't already have them:

| Tool | What it's for | Check if installed |
|---|---|---|
| Python 3.9+ | Runs the `ytb` script | `python3 --version` |
| `ffmpeg` | Merges the separate video and audio files into one `.mp4` | `ffmpeg -version` |
| `git` | Downloads the PO-token helper | `git --version` |
| Node.js 20+ and `npm` | Installs the PO-token helper's dependencies | `node --version` |
| `deno` 2.0+ | Runs the PO-token helper (no server needed) | `deno --version` |

If any are missing, install them:

```bash
# ffmpeg and git (Ubuntu/Debian)
sudo apt update
sudo apt install ffmpeg git -y

# Node.js — easiest via nvm (https://github.com/nvm-sh/nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
nvm install --lts

# Deno
curl -fsSL https://deno.land/install.sh | sh
# then add this line to your ~/.bashrc (the installer usually does it for you):
#   export PATH="$HOME/.deno/bin:$PATH"
```

Close and reopen your terminal (or run `source ~/.bashrc`) after installing
Node and Deno so the `node`, `npm`, and `deno` commands are on your `PATH`.

---

## 2. Create the project folder and a Python virtual environment

Keeping this in its own virtual environment (venv) means it won't clash
with any other Python packages on your system.

```bash
mkdir -p ~/.local/share/ytb
cd ~/.local/share/ytb
python3 -m venv venv
```

## 3. Install the Python packages

```bash
~/.local/share/ytb/venv/bin/pip install --upgrade pip
~/.local/share/ytb/venv/bin/pip install yt-dlp bgutil-ytdlp-pot-provider
```

- `yt-dlp` — does the actual downloading.
- `bgutil-ytdlp-pot-provider` — a yt-dlp plugin that knows how to ask the
  PO-token helper (set up in the next step) for a token, and hands it to
  yt-dlp automatically.

## 4. Set up the PO-token helper

This is the piece that lets yt-dlp get past YouTube's bot checks for
adaptive/HD formats. It runs as a short-lived script each time a download
starts — there's no background server to keep running.

```bash
cd ~
git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git
cd bgutil-ytdlp-pot-provider/server
npm install
```

That's it — `yt-dlp` will find it automatically at
`~/bgutil-ytdlp-pot-provider/server` the next time it needs a token
(no extra configuration required, as long as it's cloned to that exact
path in your home folder).

> The first time you actually run a download, Deno will download and
> cache a few hundred small support packages for this script. That's
> normal and only happens once.

## 5. Add the `ytb.py` script

Save the following as `~/.local/share/ytb/ytb.py`:

```python
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
```

## 6. Create the `ytb` command

Create a launcher script that runs `ytb.py` with the venv's Python
(so it always uses the packages installed in step 3, not your system
Python):

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/ytb << 'EOF'
#!/bin/bash
exec ~/.local/share/ytb/venv/bin/python ~/.local/share/ytb/ytb.py "$@"
EOF
chmod +x ~/.local/bin/ytb
```

## 7. Make sure `~/.local/bin` is on your `PATH`

Check with:

```bash
echo $PATH | tr ':' '\n' | grep local/bin
```

If nothing prints, add this line to `~/.bashrc` (or `~/.zshrc`) and
restart your terminal:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## 8. Test it

```bash
ytb "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
ytb "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o
```

You should see a `.mp4` (or `.m4a` for audio) file appear in
`~/Downloads`.

---

## Usage

```bash
ytb <youtube_url>                 # download video (up to 1080p) as .mp4
ytb <youtube_url> -o              # download audio only, as .m4a
ytb <youtube_url> -d ~/Videos     # choose a different save folder
```

## How it works

1. `ytb.py` calls `yt-dlp` with `--extractor-args youtube:player_client=mweb`.
   The `mweb` (mobile web) client is one of the few YouTube "clients"
   that still exposes the full quality list (144p up to 4K) once a PO
   token is supplied.
2. When yt-dlp needs a PO token, the `bgutil-ytdlp-pot-provider` plugin
   (installed in step 3) runs a small Deno script from
   `~/bgutil-ytdlp-pot-provider/server` to generate one on the spot.
   No persistent server, no account, nothing leaves your machine except
   the normal request to YouTube.
3. `-f "bv*[height<=1080]+ba/b[height<=1080]"` tells yt-dlp: pick the
   best video track that's 1080p or lower, plus the best audio track,
   and merge them. (Raise `MAX_HEIGHT` in `ytb.py` if you want 4K
   instead — just know the files get much bigger.)
4. `--merge-output-format mp4` tells yt-dlp to hand the merge job to
   `ffmpeg` and produce a single `.mp4`.

## Troubleshooting

**`HTTP Error 403: Forbidden` on a specific video, but others work fine**
Some videos are restricted by YouTube itself (usually a copyright/Content
ID claim) so that only the old low-quality 360p stream is servable to
third-party tools, no matter what client or token you use. This isn't
something the script can work around — if you re-run `ytb` on that video
you'll still get 360p (or the tool will report the failure if even that
is blocked). Try a different video to confirm the setup itself is fine.

**Every video fails with a bot-detection / 403 error**
- Update yt-dlp — YouTube changes things often and yt-dlp ships fixes
  frequently:
  ```bash
  ~/.local/share/ytb/venv/bin/pip install --upgrade yt-dlp
  ```
- Make sure `deno --version` reports 2.0 or higher.
- Make sure `~/bgutil-ytdlp-pot-provider/server/node_modules` exists
  (re-run `npm install` there if not).

**"ffmpeg not found" / merging fails**
Install it with `sudo apt install ffmpeg` and confirm `ffmpeg -version`
works in a fresh terminal.

**`ytb: command not found`**
`~/.local/bin` isn't on your `PATH` — see step 7 above.

## Notes

- Works on Linux (uses `notify-send` for a desktop notification if
  available, or a terminal bell as a fallback — no Windows-only APIs).
- Filenames are taken directly from the video's title via yt-dlp's
  output template; special characters are handled automatically.
- This project is open-source and free to use for personal purposes.
