"""
Revision scheduling re-exports.

The primary implementation lives in :mod:`tutor.memory.revision_scheduler` so API
routes and memory stay aligned. This module exists so forgetting-related imports
can live under ``tutor.forgetting`` without duplicating scheduling logic.
"""

from tutor.memory.revision_scheduler import RevisionScheduler, build_revision_schedule

__all__ = ["RevisionScheduler", "build_revision_schedule"]
