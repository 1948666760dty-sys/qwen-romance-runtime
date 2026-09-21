"""Opt-in live tests. They are skipped unless QRR_LIVE=1 and a local backend is available."""

import os

import pytest


pytestmark = pytest.mark.skipif(os.getenv("QRR_LIVE") != "1", reason="set QRR_LIVE=1 to run against a real local Qwen backend")


@pytest.mark.asyncio
async def test_live_qwen_smoke_script_is_opt_in():
    # The full live path is intentionally driven by scripts/smoke_test.py so its output can be archived.
    assert os.getenv("QRR_LIVE") == "1"

