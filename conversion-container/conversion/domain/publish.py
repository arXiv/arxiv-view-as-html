from dataclasses import dataclass

from arxiv.identifier import Identifier

@dataclass
class PublishPayload:
    submission_id: int
    paper_id: Identifier

    def __str__ (self):
        return f'{self.submission_id}->{self.paper_id.idv}'