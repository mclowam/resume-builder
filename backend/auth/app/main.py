from fastapi import FastAPI

from app.api.users import api_v1_router

app = FastAPI()

app.include_router(api_v1_router)

@app.get("/health")
def health():
    return {"health": "OK"}
