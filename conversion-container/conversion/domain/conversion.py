from abc import ABC, abstractmethod
from dataclasses import dataclass

from arxiv.identifier import Identifier


@dataclass
class ConversionPayload(ABC):
    identifier: Identifier | int
    single_file: bool | None

    @property
    @abstractmethod
    def name(self) -> str: ...


@dataclass
class SubmissionConversionPayload(ConversionPayload):
    identifier: int
    single_file: bool | None

    @property
    def name(self) -> str:
        return str(self.identifier)


@dataclass
class DocumentConversionPayload(ConversionPayload):
    identifier: Identifier
    is_latest: bool

    @property
    def name(self) -> str:
        # Archive-qualified serving key (arxiv-base latexml_html_path convention): squashedv keeps
        # the archive for old-style ids (astro-ph0310571v2) — bare old-style filenames are
        # per-archive sequences that collide across archives (astro-ph/9711200 vs hep-th/9711200
        # are different papers). squashedv == idv for new-style ids, so those keys are unchanged.
        return self.identifier.squashedv


@dataclass
class LaTeXMLOutput:
    returncode: int
    log: str | None
    missing_packages: list[str]
