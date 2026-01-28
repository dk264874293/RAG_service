import logging
from collections.abc import Callable, Generator
from typing import Literal, Union, overload

from flask import Flask

logger = logging.getLogger(__name__)

class Storage:
    def init_app(self, app: Flask):
        storage_factory = self.get_storage_factory()
        with app.app_context():
            self.storage_runner = storage_factory()

    def get_storage_factory():
        pass

    def save(self):
        pass

    def load(self):
        pass

    def load_once(self):
        pass

    def load_stream(self):
        pass

    def download(self):
        pass

    def exists(self):
        pass

    def delete(self):
        pass

    def scan(self):
        pass

storage = Storage()

def init_app(app: Flask):
    """供应用启动时调用的初始化入口"""
    storage.init_app(app)