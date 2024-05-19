# mp3merge-audiobooks-script
Merge books with multiple .mp3 files to one .mp3 file pr book using ffmpeg. Then at the end update Audiobookshelf.

Usage: You must have ffmpeg and python installed. Set your base path, base URL, ABS library id and ABS API key in the script.

This script will incrementally scan your audiobook library for books with multiple .mp3 files and merge them all to one .mp3 file pr book. It will then update your ABS library to reflect the changes. 
