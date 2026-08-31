"""
extractors/base.py
──────────────────
The seam that keeps TICS language-neutral. A frontend's whole job is to turn a
repository into a CodeGraph; everything downstream — pair scoring, decay,
aggregation, reporting — consumes the graph and never the source.

Only a Python frontend exists today, which matches the study's sample (all
generated backends observed so far are pure Python). Recording that as a scope
decision here, rather than letting Python assumptions leak into the scorer, is
what makes the limitation a stated one instead of a hidden one.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from validators.tics.model import CodeGraph


class ILanguageExtractor(ABC):
    """Builds a CodeGraph for one language."""

    language: str

    @abstractmethod
    def detect(self, repo_root: Path) -> bool:
        """True when this frontend can handle the repository."""

    @abstractmethod
    def build_graph(self, repo_root: Path, source_roots: list[str] | None = None) -> CodeGraph:
        """Parse first-party source under `source_roots` into a graph.

        `source_roots` bounds what counts as the candidate's own code. Left as
        None the frontend infers it; vendored and generated trees must be
        excluded either way, since a graph that includes site-packages makes
        every pair of functions reachable through library internals.
        """


def select_extractor(repo_root: Path) -> ILanguageExtractor:
    """Pick a frontend for the repository, or explain why none fits."""
    from validators.tics.extractors.python_extractor import PythonExtractor

    for extractor in (PythonExtractor(),):
        if extractor.detect(repo_root):
            return extractor
    raise NotImplementedError(
        f"no TICS language frontend handles {repo_root}. "
        "Only Python is supported; see extractors/base.py for the scope decision."
    )
