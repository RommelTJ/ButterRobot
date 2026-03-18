import asyncio
import os
from typing import Any

import websockets
import websockets.exceptions
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

OPENCLAW_WS_URL = os.getenv("OPENCLAW_WS_URL", "ws://127.0.0.1:18789")

router = APIRouter()


async def _bridge(client: WebSocket, upstream: Any) -> None:
    async def inbound() -> None:
        try:
            while True:
                data = await client.receive()
                if data.get("type") == "websocket.disconnect":
                    break
                if "text" in data:
                    await upstream.send(data["text"])
                elif "bytes" in data:
                    await upstream.send(data["bytes"])
        except (WebSocketDisconnect, Exception):
            pass

    async def outbound() -> None:
        try:
            async for message in upstream:
                if client.client_state != WebSocketState.CONNECTED:
                    break
                if isinstance(message, str):
                    await client.send_text(message)
                else:
                    await client.send_bytes(message)
        except (websockets.exceptions.ConnectionClosed, Exception):
            pass

    tasks = [asyncio.create_task(inbound()), asyncio.create_task(outbound())]
    _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@router.websocket("/{path:path}")
async def openclaw_proxy(websocket: WebSocket, path: str) -> None:
    await websocket.accept()

    target = f"{OPENCLAW_WS_URL}/{path}"
    query_string: bytes = websocket.scope.get("query_string", b"")
    if query_string:
        target += f"?{query_string.decode()}"

    extra_headers = {}
    if auth := websocket.headers.get("authorization"):
        extra_headers["authorization"] = auth

    try:
        async with websockets.connect(target, additional_headers=extra_headers) as upstream:
            await _bridge(websocket, upstream)
    except (OSError, websockets.exceptions.WebSocketException):
        pass
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
