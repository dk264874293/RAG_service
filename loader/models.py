'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-05 08:26:44
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-05 08:49:00
FilePath: /RAG_service/loader/models.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEcla
'''
from typing import Any
from pydantic import BaseModel,Field

class ChildDocument(BaseModel):
    """Class for storing a piece of text and associated metadata."""

    page_content: str

    vector: list[float] | None = None

    """Arbitrary metadata about the page content (e.g., source, relationships to other
        documents, etc.).
    """
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttachmentDocument(BaseModel):
    """Class for storing a piece of text and associated metadata."""

    page_content: str

    provider: str | None = "dify"

    vector: list[float] | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)



class Document(BaseModel):
    page_content:str
    vector: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provider:str | None = 'dify'
    children: list[ChildDocument] | None = None
    attachments: list[AttachmentDocument]  | None = None