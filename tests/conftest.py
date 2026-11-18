"""Test-wide configuration."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pmsm_ai.dataset import PMSMDesignDatasetGenerator  # noqa: E402
from pmsm_ai.service import PredictionService  # noqa: E402
from pmsm_ai.surrogate import RandomForestSurrogate, TrainingConfig  # noqa: E402


@pytest.fixture(scope="session")
def tiny_bundle():
    """Provide a fast real random-forest bundle for UI and service tests."""

    frame = PMSMDesignDatasetGenerator(seed=7).generate(240)
    config = TrainingConfig(seed=7, estimators=20, max_depth=8, min_samples_leaf=3)
    return RandomForestSurrogate(config=config).train(frame)


@pytest.fixture(scope="session")
def tiny_service(tiny_bundle):
    """Provide prediction services backed by the tiny model bundle."""

    return PredictionService(tiny_bundle)
