from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict , Optional
from chain.chat_chain import ChatChain
import uvicorn

app = FastAPI(
    title="智能客服系统",
    description="智能客服系统API",
    version="1.0.0",
    docs_url="/docs",
)

chat_chain = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    session_id: str

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global chat_chain
    chat_chain = ChatChain()
    await chat_chain.initialize()

@app.post('/chat',response_model=ChatResponse)
async def chat_endpoint(request:ChatRequest):
    """处理聊天请求"""
    try:
        reply = await chat_chain.process_message(
            message=request.message,
            history=[]
        )

        return ChatResponse(reply=reply,session_id=request.session_id)
    except Exception as e:
        print(f"处理消息时出错: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8890)