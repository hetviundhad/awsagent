import os
import re
import json
import shutil
from typing import Optional, Dict, Any, List, Tuple
import httpx
from backend.app.core.config import settings

def parse_vtt_captions(vtt_text: str) -> List[Dict[str, Any]]:
    segments = []
    pattern = re.compile(r'(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})')
    lines = vtt_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = pattern.search(line)
        if m:
            h1, m1, s1, ms1, h2, m2, s2, ms2 = m.groups()
            start = (int(h1) if h1 else 0) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000.0
            end = (int(h2) if h2 else 0) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000.0
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() and not pattern.search(lines[i]):
                clean = re.sub(r'<[^>]+>', '', lines[i].strip())
                if clean:
                    text_lines.append(clean)
                i += 1
            text = " ".join(text_lines).strip()
            if text and end > start:
                segments.append({
                    "start": start,
                    "end": end,
                    "text": text,
                    "source": "captions"
                })
        else:
            i += 1
    return segments

def parse_json3_captions(json3_data: dict) -> List[Dict[str, Any]]:
    segments = []
    events = json3_data.get("events", [])
    for ev in events:
        start_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurationMs", 0)
        segs = ev.get("segs", [])
        text = "".join([s.get("utf8", "") for s in segs]).replace("\n", " ").strip()
        if text and text != "\n" and dur_ms > 0:
            start = start_ms / 1000.0
            end = (start_ms + dur_ms) / 1000.0
            segments.append({
                "start": start,
                "end": max(end, start + 0.5),
                "text": text,
                "source": "captions"
            })
    return segments

class StorageService:
    def __init__(self):
        self.upload_dir = os.path.join(settings.STORAGE_DIR, "uploads")
        self.figures_dir = os.path.join(settings.STORAGE_DIR, "figures")
        self.keyframes_dir = os.path.join(settings.STORAGE_DIR, "keyframes")
        self.audio_dir = os.path.join(settings.STORAGE_DIR, "audio")
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.figures_dir, exist_ok=True)
        os.makedirs(self.keyframes_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)

    def save_file(self, filename: str, content_bytes: bytes) -> str:
        safe_filename = filename.replace(" ", "_")
        dest_path = os.path.join(self.upload_dir, safe_filename)
        with open(dest_path, "wb") as f:
            f.write(content_bytes)
        
        from backend.app.services.database import db
        if db.supabase_client:
            def _upload_storage():
                try:
                    bucket = settings.SUPABASE_STORAGE_BUCKET
                    db.supabase_client.storage.from_(bucket).upload(safe_filename, content_bytes)
                except Exception as e:
                    pass
            try:
                db._sync_executor.submit(_upload_storage)
            except Exception:
                pass

        return dest_path

    def get_file_path(self, filename: str) -> Optional[str]:
        p = os.path.join(self.upload_dir, filename.replace(" ", "_"))
        if os.path.exists(p):
            return p
        return None

    def extract_youtube_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def download_youtube_audio_and_captions(self, url: str) -> Dict[str, Any]:
        """
        Extracts YouTube media using yt-dlp.
        Attempts to fetch captions first (flagged as source='captions').
        Downloads audio stream for Whisper fallback or supplementary alignment.
        """
        import yt_dlp

        video_id = self.extract_youtube_video_id(url) or "video"
        canonical_url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else url

        # 1. Probe info and captions without full download
        info_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True
        }
        
        info = None
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            try:
                info = ydl.extract_info(canonical_url, download=False)
            except Exception as e:
                raise RuntimeError(f"Unable to access YouTube video at {url}: {e}") from e

        if not info:
            raise RuntimeError(f"No metadata returned by yt-dlp for {url}")

        title = info.get("title") or f"YouTube Video {video_id}"
        duration = float(info.get("duration") or 0.0)
        uploader = info.get("uploader") or info.get("channel") or "YouTube"

        # 2. Check for captions (manual or auto)
        caption_segments = []
        subtitles = info.get("subtitles") or {}
        auto_subtitles = info.get("automatic_captions") or {}

        # Prioritize manual English/Hindi, then auto English/Hindi, then any available subtitles
        chosen_subs = None
        for lang_prefix in ["en", "hi"]:
            match = next((subtitles[k] for k in subtitles if k.startswith(lang_prefix)), None)
            if match:
                chosen_subs = match
                break
        if not chosen_subs:
            for lang_prefix in ["en", "hi"]:
                match = next((auto_subtitles[k] for k in auto_subtitles if k.startswith(lang_prefix)), None)
                if match:
                    chosen_subs = match
                    break
        if not chosen_subs and subtitles:
            first_lang = list(subtitles.keys())[0]
            chosen_subs = subtitles[first_lang]
        elif not chosen_subs and auto_subtitles:
            first_lang = list(auto_subtitles.keys())[0]
            chosen_subs = auto_subtitles[first_lang]

        if chosen_subs:
            # Look for json3 or vtt formats
            sub_format = next((fmt for fmt in chosen_subs if fmt.get("ext") == "json3"), None)
            if not sub_format:
                sub_format = next((fmt for fmt in chosen_subs if fmt.get("ext") == "vtt"), None)
            if not sub_format and chosen_subs:
                sub_format = chosen_subs[0]

            if sub_format and sub_format.get("url"):
                try:
                    with httpx.Client(timeout=15.0) as client:
                        sub_resp = client.get(sub_format["url"])
                    if sub_resp.status_code == 200:
                        content_type = sub_resp.headers.get("content-type", "")
                        ext = sub_format.get("ext", "")
                        if ext == "json3" or "json" in content_type:
                            caption_segments = parse_json3_captions(sub_resp.json())
                        else:
                            caption_segments = parse_vtt_captions(sub_resp.text)
                except Exception as ex:
                    print(f"[YouTube Ingestion] Notice: Failed parsing remote captions: {ex}")

        # 3. Download audio file if captions missing or for complete processing
        audio_target_path = os.path.join(self.audio_dir, f"yt_{video_id}.m4a")
        if os.path.exists(audio_target_path) and os.path.getsize(audio_target_path) > 24 * 1024 * 1024:
            try:
                os.remove(audio_target_path)
            except Exception:
                pass
        
        if not os.path.exists(audio_target_path):
            download_opts = {
                "format": "139/249/250/ba[filesize<24M]/ba[abr<=64]/m4a/bestaudio/best",
                "outtmpl": os.path.join(self.audio_dir, f"yt_{video_id}.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
            }
            try:
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    ydl.download([canonical_url])
            except Exception as dl_err:
                # If audio download failed but we already have captions, proceed with captions
                if not caption_segments:
                    raise RuntimeError(f"Failed to download audio from YouTube video: {dl_err}") from dl_err

        # Find the actual downloaded audio file if extension was different (e.g. webm)
        actual_audio_file = None
        for candidate_ext in ["m4a", "webm", "mp3", "opus", "wav"]:
            cand = os.path.join(self.audio_dir, f"yt_{video_id}.{candidate_ext}")
            if os.path.exists(cand):
                actual_audio_file = cand
                break

        return {
            "video_id": video_id,
            "canonical_url": canonical_url,
            "title": title,
            "duration": duration,
            "uploader": uploader,
            "audio_path": actual_audio_file,
            "caption_segments": caption_segments,
            "source_type": "captions" if caption_segments else "whisper"
        }

storage = StorageService()
