"""Tests for job duration estimates."""

from src.utils.job_estimate import estimate_job_duration_seconds


def test_parallel_five_skus_five_sites_about_four_minutes() -> None:
    seconds = estimate_job_duration_seconds(
        5,
        5,
        scrape_sites_sequential=False,
        max_concurrent_scrapers=3,
    )
    # 2 waves x 18s + 7s inter-SKU delay, x5 SKUs ~ 215s.
    assert 170 <= seconds <= 220


def test_parallel_two_skus_two_sites() -> None:
    seconds = estimate_job_duration_seconds(
        2,
        2,
        scrape_sites_sequential=False,
        max_concurrent_scrapers=3,
    )
    assert seconds == 50
