from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .core.database import engine
from .api.routers.user import router as user_router
from .api.routers.auth import router as auth_router  
from .api.routers.vacancy import router as vacancy_router
from .models.db_models import Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HH Job Application API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(vacancy_router)

@app.get("/")
async def root():
    return {"message": "HH Job Application API"}