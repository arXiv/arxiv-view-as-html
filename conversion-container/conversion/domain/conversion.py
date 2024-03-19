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

class SubmissionConversionPayload (ConversionPayload):
    identifier: int

    @property
    def name (self) -> str:
        return str(self.identifier)

class DocumentConversionPayload (ConversionPayload):
    identifier: Identifier
    is_latest: bool

    @property
    def name (self) -> str:
        return self.identifier.idv

@dataclass
class LaTeXMLOutput:
    output: str
    missing_packages: List[str]