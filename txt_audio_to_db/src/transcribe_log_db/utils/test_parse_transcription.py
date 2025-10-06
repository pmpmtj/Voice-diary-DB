"""
Unit test for parse_transcription_response mapping.

This test verifies that the ingestion layer correctly maps the
transcriber output into the normalized structure used for inserts.
"""

import json

from .db_utils import TranscriptionIngestion


def test_parse_transcription_response_basic():
    ingestion = TranscriptionIngestion()
    sample = {
        "text": "hello world",
        "logprobs": None,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 2,
            "total_tokens": 12,
            "type": "tokens",
            "input_token_details": {
                "audio_tokens": 10,
                "text_tokens": 0,
            },
        },
        "_meta": {
            "model": "gpt-4o-transcribe",
            "detect_model": "gpt-4o-mini-transcribe",
            "source_file": "C:/path/to/file.m4a",
            "forced_language": False,
            "language_routing_enabled": True,
            "routed_language": "en",
            "probe_seconds": 25,
            "ffmpeg_used": False,
        },
    }

    parsed = ingestion.parse_transcription_response(sample)
    assert parsed["text"] == "hello world"
    assert parsed["model"] == "gpt-4o-transcribe"
    assert parsed["detect_model"] == "gpt-4o-mini-transcribe"
    assert parsed["source_file"].endswith("file.m4a")
    assert parsed["forced_language"] is False
    assert parsed["language_routing_enabled"] is True
    assert parsed["routed_language"] == "en"
    assert parsed["probe_seconds"] == 25
    assert parsed["ffmpeg_used"] is False
    assert parsed["usage_type"] == "tokens"
    assert parsed["input_tokens"] == 10
    assert parsed["output_tokens"] == 2
    assert parsed["total_tokens"] == 12
    assert parsed["audio_tokens"] == 10
    assert parsed["text_tokens"] == 0
    # run_uuid exists and response_json is a string holding serialized json
    assert parsed["run_uuid"]
    json.loads(parsed["response_json"])  # should not raise


