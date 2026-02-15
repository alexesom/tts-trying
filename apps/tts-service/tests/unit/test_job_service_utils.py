from app.application.job_service import JobService


def test_sanitize_filename_keeps_slug_format() -> None:
    value = JobService._sanitize_filename("My Great Audio File!!!", "https://example.com")
    assert value == "my-great-audio-file"


def test_fallback_summary_is_not_empty() -> None:
    summary = JobService._fallback_summary("hello world " * 40)
    assert summary
    assert len(summary) <= 480
