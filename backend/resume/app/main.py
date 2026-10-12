from fastapi import FastAPI

from app.api.vacancy import api_v1_router as vacancy_api_v1_router
from app.api.resume import api_v1_router as resume_api_v1_router

app = FastAPI()

app.include_router(vacancy_api_v1_router)
app.include_router(resume_api_v1_router)


@app.get("/health")
def health():
    return {"health": "OK"}
