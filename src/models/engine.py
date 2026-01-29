'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 12:59:08
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 12:59:12
FilePath: /RAG_agent/src/models/engine.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)

# ****** IMPORTANT NOTICE ******
#
# NOTE(QuantumGhost): Avoid directly importing and using `db` in modules outside of the
# `controllers` package.
#
# Instead, import `db` within the `controllers` package and pass it as an argument to
# functions or class constructors.
#
# Directly importing `db` in other modules can make the code more difficult to read, test, and maintain.
#
# Whenever possible, avoid this pattern in new code.
db = SQLAlchemy(metadata=metadata)
