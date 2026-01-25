# YouTube Downloader

A simple Python script to download YouTube videos or audio directly to your system's Downloads folder. The script supports downloading audio-only or both video and audio streams with progress tracking.

## Features

- Download YouTube videos in WebM format with the highest available resolution.
- Download audio-only streams with the highest available quality.
- Progress bars for both video and audio downloads.
- Automatic merging of video and audio into a single MP4 file using FFmpeg.
- Saves downloaded files in the system's Downloads folder.
- Handles invalid characters in file names automatically.

## Requirements

- Python 3.7 or higher
- pytubefix
- tqdm
-FFmpeg installed and added to system PATH (for merging video and audio)
- Windows OS (uses winsound for notifications)

You can install Python dependencies using pip:

`pip install pytubefix tqdm`


FFmpeg can be downloaded from https://ffmpeg.org/
and must be added to your system PATH.

## Usage

Run the script with the YouTube URL as an argument:

`python download.py <youtube_url>`

To download audio only:

`python download.py <youtube_url> -o`

Examples
`python download.py https://youtube.com/watch?v=example`
`python download.py https://youtube.com/watch?v=example -o`

## How It Works ?

The script fetches video information (title, author, duration) using pytubefix.
Depending on the mode, it downloads either the audio stream or both audio and video streams with a progress bar.
For video + audio mode, temporary files are downloaded and then merged into a single MP4 using FFmpeg.
The final file is saved in the Downloads folder with a cleaned filename to avoid invalid characters.

## Notes

Ensure FFmpeg is installed and accessible via the command line, otherwise merging will fail.
The script is designed for Windows due to the use of winsound for notification sounds.
Downloaded files are saved in the default Downloads folder for the current user.

License

This project is open-source and free to use for personal purposes.
