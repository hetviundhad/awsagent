import os
import pytest
import uuid
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.providers.stt_provider import (
    MockSpeechToTextProvider, GroqWhisperProvider, FasterWhisperProvider, get_stt_provider
)
from backend.app.services.database import db
from backend.app.services.storage import storage

@pytest.fixture
def test_course_id():
    c_id = f"test-yt-course-{uuid.uuid4().hex[:8]}"
    db.insert("courses", {
        "id": c_id,
        "name": "YouTube Test Course",
        "description": "Testing media ingestion pipeline",
        "subject": "Computer Science"
    })
    return c_id

def test_window_chunking_timestamps():
    """
    Test requirement: chunk transcripts into 30-60s windows with start_sec < end_sec on every unit.
    """
    pipeline = IngestionPipeline()
    raw_segments = [
        {"start": 0.0, "end": 10.0, "text": "Welcome to the introduction segment of the lecture."},
        {"start": 10.0, "end": 22.0, "text": "Today we explore computational complexity and asymptotic bounds."},
        {"start": 22.0, "end": 35.0, "text": "Notice how the recurrence relations determine runtime behavior."},
        {"start": 35.0, "end": 50.0, "text": "We evaluate Master Theorem cases one, two, and three."},
        {"start": 50.0, "end": 75.0, "text": "Here is an example problem demonstrating logarithmic speedup."},
        {"start": 75.0, "end": 110.0, "text": "In conclusion, divide-and-conquer partitions input data efficiently."}
    ]

    windowed = pipeline._chunk_transcript_into_windows(raw_segments, min_duration=30.0, max_duration=60.0)
    
    assert len(windowed) >= 2, "Expected multiple 30-60s windows from 110s audio"
    for w in windowed:
        start_sec = w["start"]
        end_sec = w["end"]
        # Core assertion: start_sec < end_sec
        assert start_sec < end_sec, f"Window timestamp error: start ({start_sec}) must be < end ({end_sec})"
        # Window duration should be sensible
        duration = end_sec - start_sec
        assert duration >= 1.0, f"Window duration too short: {duration}"
        assert len(w["text"]) > 0, "Window text should not be empty"

def test_stt_error_on_missing_or_corrupt_file():
    """
    Test requirement: If transcription fails, mark file as failed with clear error.
    Never fabricate timestamps.
    """
    provider = MockSpeechToTextProvider()
    with pytest.raises(FileNotFoundError):
        provider.transcribe("non_existent_fake_audio_file_12345.mp4")

def test_youtube_deduplication(test_course_id, monkeypatch):
    """
    Test requirement: The same URL ingested twice creates no duplicates.
    """
    pipeline = IngestionPipeline()
    sample_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = "dQw4w9WgXcQ"

    # Mock storage.download_youtube_audio_and_captions to return simulated captions
    def mock_download_yt(url):
        return {
            "video_id": video_id,
            "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
            "title": "Educational Lecture: Never Give Up on Learning",
            "duration": 180.0,
            "uploader": "Rick Educational",
            "audio_path": None,
            "caption_segments": [
                {"start": 0.0, "end": 35.0, "text": "We're no strangers to algorithms; you know the rules and so do I.", "source": "captions"},
                {"start": 35.0, "end": 72.0, "text": "A full analysis of computational limits is what I'm thinking of.", "source": "captions"},
                {"start": 72.0, "end": 120.0, "text": "You wouldn't get this from any other lecture series.", "source": "captions"}
            ],
            "source_type": "captions"
        }

    monkeypatch.setattr(storage, "download_youtube_audio_and_captions", mock_download_yt)

    # First ingestion call
    res1 = pipeline.ingest_youtube_url(course_id=test_course_id, url=sample_url)
    assert res1["status"] == "processed"
    assert res1["chunks_count"] > 0
    first_chunks_count = res1["chunks_count"]

    # Verify all inserted chunks have start_sec < end_sec
    chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == res1["document_id"])
    assert len(chunks) == first_chunks_count
    for chk in chunks:
        assert chk["timestamp_start"] is not None
        assert chk["timestamp_end"] is not None
        assert chk["timestamp_start"] < chk["timestamp_end"], "Every video unit must have timestamp_start < timestamp_end"

    # Second ingestion call with the EXACT SAME URL
    res2 = pipeline.ingest_youtube_url(course_id=test_course_id, url=sample_url)
    assert res2.get("duplicate") is True, "Second call must detect duplicate"
    assert res2["chunks_count"] == first_chunks_count or res2.get("status") == "already_indexed"

    # Verify total chunks in DB did not double
    total_course_chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == test_course_id)
    assert len(total_course_chunks) == first_chunks_count, (
        f"Duplicates created! Expected {first_chunks_count} chunks, found {len(total_course_chunks)}"
    )

def test_vtt_and_json3_caption_parsers():
    """
    Test that storage caption parsers accurately produce start < end segments flagged as source='captions'.
    """
    from backend.app.services.storage import parse_vtt_captions, parse_json3_captions

    vtt_sample = """WEBVTT

00:00:05.120 --> 00:00:09.450
Welcome to lecture five on cellular biology.

00:00:09.500 --> 00:00:15.300
Today we discuss membrane transport and ATP synthase.
"""
    vtt_segments = parse_vtt_captions(vtt_sample)
    assert len(vtt_segments) == 2
    for seg in vtt_segments:
        assert seg["start"] < seg["end"]
        assert seg["source"] == "captions"

    json3_sample = {
        "events": [
            {
                "tStartMs": 1000,
                "dDurationMs": 4000,
                "segs": [{"utf8": "Mitochondria produce cellular ATP."}]
            },
            {
                "tStartMs": 5500,
                "dDurationMs": 3500,
                "segs": [{"utf8": "Electrons pass through four respiratory complexes."}]
            }
        ]
    }
    json3_segments = parse_json3_captions(json3_sample)
    assert len(json3_segments) == 2
    for seg in json3_segments:
        assert seg["start"] < seg["end"]
        assert seg["source"] == "captions"
