from dataclasses import dataclass
from typing import List, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel

from arxiv.identifier import Identifier

@dataclass
class ConversionPayload (ABC):
    identifier: Union[Identifier, int]
    single_file: bool

    @property
    @abstractmethod
    def name (self) -> str:
        ...

@dataclass
class SubmissionConversionPayload (ConversionPayload):
    identifier: int

    @property
    def name (self) -> str:
        return str(self.identifier)

@dataclass
class DocumentConversionPayload (ConversionPayload):
    identifier: Identifier
    is_latest: bool

    @property
    def name (self) -> str:
        return self.identifier.idv if \
            not self.identifier.is_old_id else \
            f'{self.identifier.filename}v{self.identifier.version}'

@dataclass
class LaTeXMLOutput:
    output: str
    missing_packages: List[str]