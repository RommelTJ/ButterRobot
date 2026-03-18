import asyncio
import os
from typing import Any

import httpx
import websockets
import websockets.exceptions
from fastapi import APIRouter, Request, Response, WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

OPENCLAW_WS_URL = os.getenv("OPENCLAW_WS_URL", "ws://127.0.0.1:18789")
OPENCLAW_HTTP_URL = os.getenv("OPENCLAW_HTTP_URL", "http://127.0.0.1:18789")

_HOP_BY_HOP = frozenset({
    "connection", "keep-alive", "transfer-encoding", "te",
    "trailers", "upgrade", "proxy-authorization", "proxy-authenticate",
    "content-encoding", "content-length",
})

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
async def websocket_proxy(websocket: WebSocket, path: str) -> None:
    await websocket.accept()

    target = f"{OPENCLAW_WS_URL}/{path}"
    query_string: bytes = websocket.scope.get("query_string", b"")
    if query_string:
        target += f"?{query_string.decode()}"

    extra_headers = {}
    if auth := websocket.headers.get("authorization"):
        extra_headers["authorization"] = auth
    if origin := websocket.headers.get("origin"):
        extra_headers["origin"] = origin

    try:
        async with websockets.connect(target, additional_headers=extra_headers) as upstream:
            await _bridge(websocket, upstream)
    except (OSError, websockets.exceptions.WebSocketException):
        pass
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def http_proxy(request: Request, path: str) -> Response:
    target = f"{OPENCLAW_HTTP_URL}/{path}"
    if request.url.query:
        target += f"?{request.url.query}"

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP and k.lower() != "host"
    }

    async with httpx.AsyncClient() as client:
        upstream = await client.request(
            method=request.method,
            url=target,
            headers=headers,
            content=await request.body(),
            follow_redirects=False,
        )

    response_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
