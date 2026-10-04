from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.database.sqlite import init_db

@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield

app=FastAPI(title="Find-My-Thingy API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
