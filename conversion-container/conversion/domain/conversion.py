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
        return (
            self.identifier.idv
            if not self.identifier.is_old_id
            else f"{self.identifier.filename}v{self.identifier.version}"
        )


@dataclass
class LaTeXMLOutput:
    returncode: int
    log: str | None
    missing_packages: list[str]
