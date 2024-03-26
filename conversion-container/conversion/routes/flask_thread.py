""" FlaskThread pushes the Flask applcation context """
from typing import Any
from threading import Thread
from flask import current_app

class FlaskThread(Thread):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.app = current_app._get_current_object() # type: ignore

    def run(self) -> None:
        with self.app.app_context():
            super().run()