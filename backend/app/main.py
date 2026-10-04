from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.database.sqlite import init_db

@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield

app=FastAPI(title="Find My Thingy API", version="1.0.0", lifespan=lifespan)
frontend_origin=os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
allowed_origins=list(dict.fromkeys([frontend_origin,frontend_origin.replace("localhost","127.0.0.1")]))
app.add_middleware(CORSMiddleware,allow_origins=allowed_origins,allow_methods=["GET", "POST", "DELETE"],allow_headers=["*"])
app.include_router(router)
