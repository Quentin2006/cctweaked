import asyncio
import json
import uuid
import websockets
from enum import Enum


class Move(Enum):
    FORWARD = "turtle.forward()"
    BACK = "turtle.back()"
    LEFT = "turtle.turnLeft()"
    RIGHT = "turtle.turnRight()"
    UP = "turtle.up()"
    DOWN = "turtle.down()"


class Detect(Enum):
    FORWARD = "turtle.detect()"
    UP = "turtle.detectUp()"
    DOWN = "turtle.detectDown()"


class TurtleManager:
    def __init__(self, host="0.0.0.0", port=3000):
        self.ws = None
        self.host = host
        self.port = port
        self.commands = []
        self.connected = asyncio.Event()
        self._pending: dict[str, asyncio.Future] = {}

    async def _dispatch_loop(self):
        while True:
            if self.commands:
                code = self.commands.pop(0)
                await self.ws.send(json.dumps({"code": code}))
            await asyncio.sleep(0.5)

    async def start(self):
        async with websockets.serve(self.handle, self.host, self.port) as server:
            await self.connected.wait()
            asyncio.create_task(self._dispatch_loop())
            await server.serve_forever()

    def move(self, move: Move, distance: int):
        if distance < 0:
            raise ValueError("Distance must be non-negative")
        for _ in range(distance):
            self.commands.append(move.value)

    async def execute(self, code: str, timeout: float = 30.0):
        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending[req_id] = future
        await self.ws.send(json.dumps({"id": req_id, "code": code}))
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise

    async def handle(self, ws):
        self.ws = ws
        self.connected.set()
        try:
            async for msg in ws:
                try:
                    data = json.loads(msg)
                    req_id = data.get("id")
                    if req_id and req_id in self._pending:
                        future = self._pending.pop(req_id)
                        future.set_result(data)
                    else:
                        print(f"Response: {data}")
                except json.JSONDecodeError:
                    print(f"Message: {msg}")
        finally:
            self.ws = None
            print("Turtle disconnected")
