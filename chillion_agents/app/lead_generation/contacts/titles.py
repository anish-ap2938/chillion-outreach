"""Shared job-title matching used by website scrape and provider post-filter."""

from typing import Iterable, Optional


def matches_target_title(title: Optional[str], target_titles: Optional[Iterable[str]]) -> bool:
    """
    Case-insensitive substring match.

    "IT Director" matches "Senior IT Director".
    "Head of IT" matches "Head of IT Infrastructure".
    """
    if not title or not target_titles:
        return False
    title_lower = title.lower()
    return any(str(target).strip().lower() in title_lower for target in target_titles if target and str(target).strip())
