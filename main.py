from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict , Optional
from contextlib import asynccontextmanager

from requests import session
from chain.chat_chain import ChatChain
from session_manager import SessionManager
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
    lifespan=lifespan
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    status:str = 'success'
    reply: str
    session_id: str



@app.post('/chat',response_model=ChatResponse)
async def chat_endpoint(request:ChatRequest):
    """处理聊天请求"""
    try:
        # 获取会话历史
        history = session_manager.get_history(request.session_id)
        
        reply = await chat_chain.process_message(
            message=request.message,
            history=history
        )

        # 修复拼写错误
        session_manager.add_message(session_id=request.session_id,user_message=request.message,bot_reply=reply)

        return ChatResponse(status='success',reply=reply,session_id=request.session_id)
    except Exception as e:
        print(f"处理消息时出错: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "success"}

@app.post("/delete_history/{session_id}")
async def clear_history(session_id:str):
    """清除指定会话"""
    # 修复拼写错误
    session_manager.clear_history(session_id)
    return {"status": "success", "message": f"会话 {session_id} 已清除"}

# 修复路由路径格式
@app.get("/get_history/{session_id}")
async def get_history(session_id:str):
    """获取指定会话的历史记录"""
    # 修复拼写错误
    history = session_manager.get_history(session_id)
    return {"status": "success", "history": history}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8892)  # 修改端口为8892，避免冲突