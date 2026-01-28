from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
import os
from pathlib import Path
from datetime import datetime

from requests import session
from chain.chat_chain import ChatChain
from session_manager import SessionManager
from config import settings
import uvicorn

# 定义全局变量
chat_chain = None
session_manager = SessionManager()


# 使用新的lifespan事件处理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    global chat_chain
    chat_chain = ChatChain()
    await chat_chain.initialize()
    yield
    # 关闭时的清理工作（如果需要）
    pass


app = FastAPI(
    title="智能客服系统",
    description="智能客服系统API",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    status: str = "success"
    reply: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """处理聊天请求"""
    try:
        # 获取会话历史
        history = session_manager.get_history(request.session_id)

        reply = await chat_chain.process_message(
            message=request.message, history=history
        )

        # 修复拼写错误
        session_manager.add_message(
            session_id=request.session_id, user_message=request.message, bot_reply=reply
        )

        return ChatResponse(
            status="success", reply=reply, session_id=request.session_id
        )
    except Exception as e:
        print(f"处理消息时出错: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "success"}


@app.post("/delete_history/{session_id}")
async def clear_history(session_id: str):
    """清除指定会话"""
    # 修复拼写错误
    session_manager.clear_history(session_id)
    return {"status": "success", "message": f"会话 {session_id} 已清除"}


# 修复路由路径格式
@app.get("/get_history/{session_id}")
async def get_history(session_id: str):
    """获取指定会话的历史记录"""
    # 修复拼写错误
    history = session_manager.get_history(session_id)
    return {"status": "success", "history": history}


# ========== Markdown文件管理API ==========


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


@app.get("/api/markdown/files", response_model=MarkdownFileList)
async def get_markdown_files():
    """获取所有Markdown文件列表"""
    if not settings.markdown_editor_enabled:
        raise HTTPException(status_code=403, detail="Markdown编辑器未启用")

    files = []
    output_dir = Path(settings.markdown_output_dir)

    if not output_dir.exists():
        return MarkdownFileList(files=files)

    # 递归扫描所有.md文件
    for root, dirs, filenames in os.walk(output_dir):
        for filename in filenames:
            if filename.endswith(".md"):
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(output_dir)
                folder_name = rel_path.parent.name if rel_path.parent else ""

                # 获取文件信息
                stat = full_path.stat()
                file_size = stat.st_size
                modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()

                files.append(
                    MarkdownFile(
                        name=filename,
                        path=str(rel_path),
                        folder_name=folder_name,
                        url=f"/api/markdown/file/{rel_path}",
                        size=file_size,
                        modified_time=modified_time,
                    )
                )

    # 按修改时间排序
    files.sort(key=lambda x: x.modified_time, reverse=True)

    return MarkdownFileList(files=files)


@app.get("/api/markdown/file/{file_path:path}", response_model=MarkdownContent)
async def get_markdown_file(file_path: str):
    """读取指定Markdown文件内容"""
    if not settings.markdown_editor_enabled:
        raise HTTPException(status_code=403, detail="Markdown编辑器未启用")

    # 安全检查：防止路径遍历攻击
    output_dir = Path(settings.markdown_output_dir).resolve()
    full_path = (output_dir / file_path).resolve()

    # 确保路径在output_dir内
    if not str(full_path).startswith(str(output_dir)):
        raise HTTPException(status_code=403, detail="非法文件路径")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    if not full_path.suffix == ".md":
        raise HTTPException(status_code=400, detail="只支持Markdown文件")

    # 检查文件大小
    file_size = full_path.stat().st_size
    if file_size > settings.markdown_max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（{file_size} > {settings.markdown_max_file_size}）",
        )

    # 读取文件内容
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    rel_path = full_path.relative_to(output_dir)
    folder_name = rel_path.parent.name if rel_path.parent else ""

    return MarkdownContent(
        content=content,
        path=str(rel_path),
        name=full_path.name,
        folder_name=folder_name,
    )


@app.post("/api/markdown/file/{file_path:path}", response_model=MarkdownSaveResponse)
async def save_markdown_file(file_path: str, request: MarkdownSaveRequest):
    """保存Markdown文件"""
    if not settings.markdown_editor_enabled:
        raise HTTPException(status_code=403, detail="Markdown编辑器未启用")

    # 安全检查：防止路径遍历攻击
    output_dir = Path(settings.markdown_output_dir).resolve()
    full_path = (output_dir / file_path).resolve()

    # 确保路径在output_dir内
    if not str(full_path).startswith(str(output_dir)):
        raise HTTPException(status_code=403, detail="非法文件路径")

    if not full_path.suffix == ".md":
        raise HTTPException(status_code=400, detail="只支持Markdown文件")

    # 检查内容长度
    if len(request.content) > settings.markdown_max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"内容过长（{len(request.content)} > {settings.markdown_max_file_size}）",
        )

    # 确保目录存在
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(request.content)

    rel_path = full_path.relative_to(output_dir)

    return MarkdownSaveResponse(
        status="success", message="文件保存成功", path=str(rel_path)
    )


# ========== 静态文件服务 ==========

# 挂载React构建后的静态文件
if os.path.exists(settings.frontend_static_dir):
    app.mount(
        "/",
        StaticFiles(directory=settings.frontend_static_dir, html=True),
        name="static",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8892)  # 修改端口为8892，避免冲突
