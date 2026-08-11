"""Compatibility profiles: advisory per-channel recommendations."""

from __future__ import annotations

from .build import profile_from_probe
from .model import Profile
from .registry import get_profile, list_profiles

__all__ = [
    "Profile",
    "profile_from_probe",
    "get_profile",
    "list_profiles",
]
