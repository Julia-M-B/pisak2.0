"""
Application settings.

The scanning parameters are independent variables of the experiment, so they are
exposed as a configuration object that can be set once at start-up (see
`aac_app.cli`) instead of constants that would have to be edited in the source.

Read them through `get_scanning_settings()` at the moment they are needed - reading
them at import time would freeze whatever the defaults were before the command line
had a chance to override them.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

# default prediction model filename in the aac_app/models directory
DEFAULT_PREDICTION_MODEL_NAME = "model.pt"


@dataclass(frozen=True)
class ScanningSettings:
    """Timing and repetition parameters of the switch-scanning interface."""

    #: how long each item stays highlighted while scanning [seconds]
    highlight_time: float = 1.0

    #: delay before the first highlight when a new scan starts [seconds];
    #: gives the user a moment to react before the first item is offered
    start_delay: float = 0.25

    #: how many times scanning loops over the children before giving up
    loop_number: int = 3


_scanning_settings = ScanningSettings()


def get_scanning_settings() -> ScanningSettings:
    """Return the scanning settings currently in effect."""
    return _scanning_settings


def configure_scanning(**overrides) -> ScanningSettings:
    """
    Override scanning settings; any value left as None keeps the current one.

    Intended to be called once, at start-up, before any scanning begins.
    """
    applied = {k: v for k, v in overrides.items() if v is not None}
    global _scanning_settings
    _scanning_settings = replace(_scanning_settings, **applied)
    return _scanning_settings
