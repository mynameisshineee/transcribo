#!/usr/bin/env python3
"""Batch transcribe all Kombo sales program videos.

Uses simple_audio_to_text.transcribe_audio which saves .txt next to each video.
Then copies/consolidates transcripts into transcript.txt per lesson folder.
"""

import os
import sys
import glob
import time
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simple_audio_to_text import transcribe_audio, get_device

KOMBO_LESSONS = "/Users/shine/nucliofounders/kombo_sales_program/lessons"
MODEL = "base"  # medium has NaN issues with MPS+fp16, base is stable
LANGUAGE = "es"


def find_lessons_with_videos():
    lessons = []
    for entry in sorted(os.listdir(KOMBO_LESSONS)):
        lesson_path = os.path.join(KOMBO_LESSONS, entry)
        if not os.path.isdir(lesson_path):
            continue
        if entry in ("CONTINUAR_PROGRAMA", "EMPEZAR_PROGRAMA", ".DS_Store"):
            continue

        videos_dir = os.path.join(lesson_path, "videos")
        mp4_files = []

        if os.path.isdir(videos_dir):
            mp4_files = [
                f for f in glob.glob(os.path.join(videos_dir, "*.mp4"))
                if not f.endswith(".temp.mp4")
            ]

        mp4_files += [
            f for f in glob.glob(os.path.join(lesson_path, "*.mp4"))
            if not f.endswith(".temp.mp4")
        ]

        if mp4_files:
            transcript_path = os.path.join(lesson_path, "transcript.txt")
            already_done = os.path.exists(transcript_path)
            lessons.append({
                "name": entry,
                "path": lesson_path,
                "videos": mp4_files,
                "transcript_path": transcript_path,
                "done": already_done,
            })

    return lessons


def main():
    device = get_device()
    print(f"Device: {device}")
    print(f"Model: {MODEL}")
    print(f"Language: {LANGUAGE}\n")

    lessons = find_lessons_with_videos()
    total = len(lessons)
    pending = [l for l in lessons if not l["done"]]
    done = total - len(pending)

    print(f"Total lessons with videos: {total}")
    print(f"Already transcribed: {done}")
    print(f"Pending: {len(pending)}")
    print("=" * 60)

    for i, lesson in enumerate(pending):
        print(f"\n[{done + i + 1}/{total}] {lesson['name']}")

        # Pick the largest MP4 (main video)
        video = max(lesson["videos"], key=os.path.getsize)
        size_mb = os.path.getsize(video) / (1024 * 1024)
        print(f"  Video: {size_mb:.0f} MB")

        start = time.time()
        try:
            # transcribe_audio saves .txt next to the video and returns the path
            txt_path = transcribe_audio(video, MODEL, LANGUAGE, device)

            # Read the generated transcript
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()

                # Copy to lesson folder as transcript.txt
                with open(lesson["transcript_path"], 'w', encoding='utf-8') as f:
                    f.write(text)

                elapsed = time.time() - start
                words = len(text.split())
                print(f"  OK: {words} words in {elapsed:.0f}s")
            else:
                print(f"  Warning: No output file at {txt_path}")

        except Exception as e:
            print(f"  Error: {e}")
            continue

    print("\n" + "=" * 60)
    final_count = len([l for l in find_lessons_with_videos() if l["done"]])
    print(f"Done. {final_count}/{total} lessons have transcripts.")


if __name__ == "__main__":
    main()
