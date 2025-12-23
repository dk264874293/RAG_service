'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-01 19:22:32
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-23 15:29:08
FilePath: /RAG_service/test_langchain.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"sys.path: {sys.path}")

try:
    import langchain_core
    print(f"langchain_core version: {langchain_core.__version__}")
    print(f"langchain_core path: {langchain_core.__file__}")
except ImportError:
    print("langchain_core module not found")
