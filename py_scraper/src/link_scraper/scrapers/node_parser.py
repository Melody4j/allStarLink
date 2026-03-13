"""
Backward-compatible parser import.
"""

from ..sources.allstarlink.parser import AllStarLinkParser


class NodeParser(AllStarLinkParser):
    """Compatibility wrapper for the legacy parser import path."""
