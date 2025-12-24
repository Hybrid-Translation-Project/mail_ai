from dotenv import load_dotenv
import os

load_dotenv()

# FastAPI framework
from fastapi import FastAPI

# Router’lar
from app.routes import inbox, approval

# FastAPI uygulaması
app = FastAPI(title="Mail AI Assistant")

# Inbox (n8n) endpoint’leri
app.include_router(inbox.router)

# Onay / iptal endpoint’leri
app.include_router(approval.router)

@app.get("/")
def health():
    """
    Sistem ayakta mı kontrolü
    """
    return {"status": "OK"}
