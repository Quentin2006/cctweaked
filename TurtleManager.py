import asyncio
import websockets
from enum import Enum


class Move(Enum):
    FORWARD = "turtle.forward()"
    BACKWARD = "turtle.backward()"
    LEFT = "turtle.turnLeft()"
    RIGHT = "turtle.turnRight()"
    UP = "turtle.up()"
    DOWN = "turtle.down()"


class TurtleManager:
    def __init__(self, host="0.0.0.0", port=3000):
        self.ws = None
        self.host = host
        self.port = port

    async def start(self):
        async with websockets.serve(
            self.handle,
            self.host,
            self.port,
        ):
            await asyncio.Future()

    async def move(self, move: Move, distance: int):
        if distance < 0:
            raise ValueError("Distance must be non-negative")
        for _ in range(distance):
            await self.send(move.value)

    async def handle(self, ws):
        self.ws = ws
        async for msg in ws:
            print(f"Message: {msg}")

    async def send(self, command):
        if self.ws:
            await self.ws.send(command)
