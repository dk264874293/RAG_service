from pydantic import BaseModel
from typing import List


class MarkdownFile(BaseModel):
    name: str
    path: str
    folder_name: str
    url: str
    size: int
    modified_time: str


class MarkdownFileList(BaseModel):
    files: List[MarkdownFile]


class MarkdownContent(BaseModel):
    content: str
    path: str
    name: str
    folder_name: str


class MarkdownSaveRequest(BaseModel):
    content: str


class MarkdownSaveResponse(BaseModel):
    status: str
    message: str
    path: str
