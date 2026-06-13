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
        self.commands = []
        self.connected = asyncio.Event()

    async def _dispatch_loop(self):
        while True:
            if self.commands:
                await self.send(self.commands)
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

    async def handle(self, ws):
        self.ws = ws
        self.connected.set()
        async for msg in ws:
            print(f"Message: {msg}")

    async def send(self, command):
        if self.ws:
            await self.ws.send(command[0])
            command.pop(0)
