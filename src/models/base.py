'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 12:57:31
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 12:58:49
FilePath: /RAG_agent/src/models/base.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column
from .engine import metadata

class Base(DeclarativeBase):
    metadata = metadata
