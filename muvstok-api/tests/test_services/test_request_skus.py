"""Ingestion validation: duplicates are preserved (N in → N out)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.requests import CreateMuvstokJobRequest

CALLBACK = "https://example.com/webhook/muvstok-result"


def test_duplicates_are_preserved_in_order():
    request = CreateMuvstokJobRequest(skus=["A", "A", " b ", "A"], callback_url=CALLBACK)
    assert request.skus == ["A", "A", "b", "A"]


def test_empty_sku_rejected():
    with pytest.raises(ValidationError):
        CreateMuvstokJobRequest(skus=["A", "   "], callback_url=CALLBACK)


def test_oversized_sku_rejected():
    with pytest.raises(ValidationError):
        CreateMuvstokJobRequest(skus=["x" * 129], callback_url=CALLBACK)
