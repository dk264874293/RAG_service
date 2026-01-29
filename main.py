'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-11-30 10:01:36
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-29 11:19:18
FilePath: /RAG_service/main.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
"""
主程序入口文件

此文件作为应用程序的入口点，负责启动 src/app.py 中的应用
"""

import uvicorn
from src.app import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )