from fastapi import FastAPI

from app.proxy import router as proxy_router

app = FastAPI()


@app.get("/health")
def health() -> str:
    return "Hello from ButterRobot!"


app.include_router(proxy_router)
