'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-21 15:50:13
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-23 15:29:18
FilePath: /RAG_service/chain/mcp/map_fast.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
import nest_asyncio

nest_asyncio.apply()

app = FastAPI()

mcp = FastApiMCP(
    app,
    name="my_mcp_api",
    # describe_all_response=True,
    # describe_full_response=True
)

mcp.mount()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)