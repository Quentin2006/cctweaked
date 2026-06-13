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


class Inspect(Enum):
    FORWARD = "local ok, data = turtle.inspect(); if ok then return data.name else return 'none' end"
    UP = "local ok, data = turtle.inspectUp(); if ok then return data.name else return 'none' end"
    DOWN = "local ok, data = turtle.inspectDown(); if ok then return data.name else return 'none' end"


class TurtleManager:
    def __init__(self, host="0.0.0.0", port=3000, blocks_file="web/blocks.txt"):
        self.ws = None
        self.host = host
        self.port = port
        self.blocks_file = blocks_file
        self.commands: list[tuple[Move, str]] = []
        self.connected = asyncio.Event()
        self._pending: dict[str, asyncio.Future] = {}

        self.x = 0
        self.y = 0
        self.z = 0
        # facing: 0=north(-Z), 1=east(+X), 2=south(+Z), 3=west(-X)
        self.facing = 0

    def _facing_vector(self) -> tuple[int, int]:
        if self.facing == 0:
            return (0, -1)   # north
        elif self.facing == 1:
            return (1, 0)    # east
        elif self.facing == 2:
            return (0, 1)    # south
        else:
            return (-1, 0)   # west

    def _update_position(self, move: Move) -> None:
        if move == Move.FORWARD:
            dx, dz = self._facing_vector()
            self.x += dx
            self.z += dz
        elif move == Move.BACK:
            dx, dz = self._facing_vector()
            self.x -= dx
            self.z -= dz
        elif move == Move.UP:
            self.y += 1
        elif move == Move.DOWN:
            self.y -= 1
        elif move == Move.LEFT:
            self.facing = (self.facing - 1) % 4
        elif move == Move.RIGHT:
            self.facing = (self.facing + 1) % 4

    def _get_block_pos(self, direction: str) -> tuple[int, int, int]:
        d = direction.upper()
        if d == "UP":
            return (self.x, self.y + 1, self.z)
        elif d == "DOWN":
            return (self.x, self.y - 1, self.z)
        elif d in ("FORWARD", "FRONT"):
            dx, dz = self._facing_vector()
            return (self.x + dx, self.y, self.z + dz)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    def _save_block(self, pos: tuple[int, int, int], block_name: str) -> None:
        x, y, z = pos
        entry = f"{x},{y},{z},{block_name}"
        lines: list[str] = []
        found = False
        try:
            with open(self.blocks_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",", 3)
                    if (
                        len(parts) == 4
                        and int(parts[0]) == x
                        and int(parts[1]) == y
                        and int(parts[2]) == z
                    ):
                        lines.append(entry)
                        found = True
                    else:
                        lines.append(line)
        except FileNotFoundError:
            pass

        if not found:
            lines.append(entry)

        with open(self.blocks_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    async def _dispatch_loop(self):
        while True:
            if self.commands:
                move, code = self.commands.pop(0)
                await self.ws.send(json.dumps({"code": code}))
                self._update_position(move)
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
            self.commands.append((move, move.value))

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

    async def inspect_block(self, direction: str) -> str | None:
        side = Inspect[direction.upper()]
        result = await self.execute(side.value)
        block = result.get("result")
        if block and block != "none":
            pos = self._get_block_pos(direction)
            self._save_block(pos, block)
            return block
        return None

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
