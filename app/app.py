from fastapi import FastAPI

from app.proxy import router as proxy_router

app = FastAPI()
app.include_router(proxy_router)


@app.get("/")
def hello() -> str:
    return "Hello from ButterRobot!"
