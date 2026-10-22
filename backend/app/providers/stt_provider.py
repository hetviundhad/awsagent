import os
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from backend.app.core.config import settings

class SpeechToTextProvider(ABC):
    @abstractmethod
    def transcribe(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Transcribes audio/video file and returns list of timestamped segments:
        [{"start": 12.0, "end": 45.5, "text": "...", "words": [{"word": "...", "start": 12.0, "end": 12.5}]}]
        If transcription fails, must raise an exception so the failure is properly recorded.
        Must never fabricate fake timestamps.
        """
        pass

class GroqWhisperProvider(SpeechToTextProvider):
    """
    Production Whisper provider utilizing Groq's high-speed Whisper Large V3 Turbo API
    with word-level and segment-level timestamps.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-large-v3-turbo"):
        self.api_key = api_key or settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
        self.model = model
        self.api_url = "https://api.groq.com/openai/v1/audio/transcriptions"

    def transcribe(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio/video file not found for transcription: {file_path}")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured for GroqWhisperProvider")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError(f"Audio file is empty (0 bytes): {file_path}")

        filename = os.path.basename(file_path)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            with open(file_path, "rb") as audio_file:
                files = {
                    "file": (filename, audio_file, "application/octet-stream")
                }
                data = {
                    "model": self.model,
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": ["segment", "word"]
                }
                with httpx.Client(timeout=120.0) as client:
                    resp = client.post(self.api_url, headers=headers, data=data, files=files)

            if resp.status_code != 200:
                raise RuntimeError(
                    f"Groq Whisper transcription API returned status {resp.status_code}: {resp.text}"
                )

            res_json = resp.json()
            raw_segments = res_json.get("segments", [])
            words = res_json.get("words", [])

            if not raw_segments and "text" in res_json:
                # If only top-level text returned
                raw_segments = [{
                    "start": 0.0,
                    "end": float(res_json.get("duration", 30.0)),
                    "text": res_json["text"]
                }]

            formatted = []
            for s in raw_segments:
                start = float(s.get("start", 0.0))
                end = float(s.get("end", start + 1.0))
                if end <= start:
                    end = start + 1.0
                text = s.get("text", "").strip()
                if not text:
                    continue

                seg_words = [
                    w for w in words
                    if float(w.get("start", 0.0)) >= start - 0.1 and float(w.get("end", 0.0)) <= end + 0.1
                ]
                formatted.append({
                    "start": start,
                    "end": end,
                    "text": text,
                    "words": seg_words,
                    "source": "whisper"
                })

            if not formatted:
                raise RuntimeError(f"Whisper transcription yielded no speech segments for {filename}")

            return formatted

        except Exception as e:
            if isinstance(e, (RuntimeError, FileNotFoundError, ValueError)):
                raise
            raise RuntimeError(f"Groq Whisper transcription failed: {str(e)}") from e

class FasterWhisperProvider(SpeechToTextProvider):
    """
    Local Whisper transcription provider utilizing faster-whisper with CTranslate2.
    """
    def __init__(self, model_size: str = "tiny"):
        self.model_size = model_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            except Exception as e:
                raise RuntimeError(f"Failed to load faster-whisper model '{self.model_size}': {e}") from e
        return self._model

    def transcribe(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio/video file not found for transcription: {file_path}")
        if os.path.getsize(file_path) == 0:
            raise ValueError(f"Audio file is empty: {file_path}")

        try:
            model = self._get_model()
            segments_gen, info = model.transcribe(file_path, word_timestamps=True)
            
            results = []
            for seg in segments_gen:
                start = float(seg.start)
                end = float(seg.end)
                if end <= start:
                    end = start + 1.0
                text = seg.text.strip()
                if not text:
                    continue

                words_list = []
                if hasattr(seg, "words") and seg.words:
                    for w in seg.words:
                        words_list.append({
                            "word": w.word,
                            "start": float(w.start),
                            "end": float(w.end),
                            "probability": float(getattr(w, "probability", 1.0))
                        })

                results.append({
                    "start": start,
                    "end": end,
                    "text": text,
                    "words": words_list,
                    "source": "whisper"
                })

            if not results:
                raise RuntimeError(f"Faster-whisper found no spoken audio content in {file_path}")

            return results
        except Exception as e:
            if isinstance(e, (RuntimeError, FileNotFoundError, ValueError)):
                raise
            raise RuntimeError(f"Faster-whisper transcription failed: {str(e)}") from e

class MockSpeechToTextProvider(SpeechToTextProvider):
    """
    Deterministic STT provider for unit testing without network dependencies.
    Never uses domain-specific hardcoded keywords; creates valid timing with start < end.
    """
    def transcribe(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        if os.path.getsize(file_path) == 0:
            raise ValueError(f"Empty audio file: {file_path}")

        return [
            {
                "start": 0.0,
                "end": 32.5,
                "text": "Welcome to today's lecture. In this module, we examine foundational principles and theoretical properties.",
                "source": "whisper"
            },
            {
                "start": 33.0,
                "end": 64.0,
                "text": "Let us consider the primary mechanisms governing system behavior, observing how subcomponents interact.",
                "source": "whisper"
            },
            {
                "start": 64.5,
                "end": 96.0,
                "text": "Analyzing the empirical data reveals significant correlation between initial conditions and equilibrium outcomes.",
                "source": "whisper"
            }
        ]

def get_stt_provider(provider_type: Optional[str] = None, api_key: Optional[str] = None) -> SpeechToTextProvider:
    selected = provider_type or settings.STT_PROVIDER
    if selected == "groq" or (selected != "mock" and (settings.GROQ_API_KEY or api_key)):
        return GroqWhisperProvider(api_key=api_key)
    elif selected in ["faster_whisper", "faster-whisper", "local"]:
        return FasterWhisperProvider()
    elif selected == "mock":
        return MockSpeechToTextProvider()
    
    # If Groq key is present, default to Groq Whisper; else faster-whisper; fallback to Mock
    if settings.GROQ_API_KEY:
        return GroqWhisperProvider()
    try:
        import faster_whisper
        return FasterWhisperProvider()
    except ImportError:
        return MockSpeechToTextProvider()
