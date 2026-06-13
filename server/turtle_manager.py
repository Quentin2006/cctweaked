"""WebSocket server + Lua dispatch + position tracking for turtle control."""

import asyncio
import json
import uuid
import time
import websockets
from server.enums import (
    Move, Action, Inspect, Sense, InventoryOp,
    DropOp, SuckOp, FuelOp, EquipmentOp, CraftOp,
)


class TurtleConnection:
    def __init__(self, turtle_id: str, ws):
        self.id = turtle_id
        self.ws = ws
        self.connected = True
        self.x = 0
        self.y = 0
        self.z = 0
        self.facing = 0
        self.selected_slot = 1
        self.last_active = time.time()

    async def send(self, message):
        if self.ws and self.connected:
            try:
                await self.ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                self.connected = False

    async def recv(self):
        if self.ws and self.connected:
            try:
                return await self.ws.recv()
            except websockets.exceptions.ConnectionClosed:
                self.connected = False
        return None


class TurtleManager:
    def __init__(self, blocks_file="data/blocks.txt"):
        self.turtles = {}
        self.pending = []
        self.lock = asyncio.Lock()
        self._current_turtle_id = None
        self.blocks_file = blocks_file
        self.x = 0
        self.y = 0
        self.z = 0
        self.facing = 0
        self._dispatch_task = None

    @property
    def _current(self):
        return self.turtles.get(self._current_turtle_id)

    @_current.setter
    def _current(self, value):
        pass

    @property
    def turtle_count(self):
        return len(self.turtles)

    async def get_inventory_state(self):
        raise NotImplementedError("Subclasses must implement")

    def list_turtles(self):
        return [
            {
                "id": tid,
                "x": t.x,
                "y": t.y,
                "z": t.z,
                "facing": t.facing,
                "connected": t.connected,
                "last_active": t.last_active,
            }
            for tid, t in self.turtles.items()
        ]

    def move(self, direction: Move, distance: int = 1):
        for _ in range(distance):
            self.pending.append(direction.value)
        self._update_position(direction, distance)

    def _update_position(self, direction: Move, distance: int):
        conn = self._current
        if not conn:
            conn = self
        if direction == Move.FORWARD:
            if conn.facing == 0:
                conn.z -= distance
            elif conn.facing == 1:
                conn.x += distance
            elif conn.facing == 2:
                conn.z += distance
            elif conn.facing == 3:
                conn.x -= distance
        elif direction == Move.BACK:
            if conn.facing == 0:
                conn.z += distance
            elif conn.facing == 1:
                conn.x -= distance
            elif conn.facing == 2:
                conn.z -= distance
            elif conn.facing == 3:
                conn.x += distance
        elif direction == Move.LEFT:
            conn.facing = (conn.facing - 1) % 4
        elif direction == Move.RIGHT:
            conn.facing = (conn.facing + 1) % 4
        elif direction == Move.UP:
            conn.y += distance
        elif direction == Move.DOWN:
            conn.y -= distance

    def _resolve_pos(self, connection):
        if connection is None:
            return self.x, self.y, self.z
        return connection.x, connection.y, connection.z

    def _resolve_facing(self, connection):
        if connection is None:
            return self.facing
        return connection.facing

    async def execute(self, lua_code: str, timeout: float = 5.0) -> str:
        conn = self._current
        if not conn or not conn.connected:
            raise ConnectionError("turtle not connected")
        req_id = uuid.uuid4().hex[:8]
        payload = json.dumps({"code": lua_code, "request_id": req_id})
        await conn.send(payload)
        while True:
            raw = await asyncio.wait_for(conn.recv(), timeout=timeout)
            if not raw:
                raise ConnectionError("turtle not connected")
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("request_id") == req_id:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", "")
        raise asyncio.TimeoutError("turtle did not respond")

    async def inspect_block(self, direction: str) -> dict | None:
        direction = direction.upper()
        if direction == "UP":
            code = Inspect.UP.value
        elif direction == "DOWN":
            code = Inspect.DOWN.value
        else:
            code = Inspect.FORWARD.value
        result = await self.execute(code)
        if result and result != "none":
            self._save_block(direction, result)
            return result
        return None

    def _save_block(self, direction: str, name: str):
        conn = self._current
        x, y, z = self._resolve_pos(conn)
        facing = self._resolve_facing(conn)
        if direction == "FORWARD":
            if facing == 0:
                z -= 1
            elif facing == 1:
                x += 1
            elif facing == 2:
                z += 1
            elif facing == 3:
                x -= 1
        elif direction == "UP":
            y += 1
        elif direction == "DOWN":
            y -= 1
        try:
            with open(self.blocks_file, "a") as f:
                f.write(f"{x},{y},{z},{name}\n")
        except OSError:
            pass

    async def dig(self, direction: str) -> bool:
        direction = direction.upper()
        if direction == "UP":
            code = Action.DIG_UP.value
        elif direction == "DOWN":
            code = Action.DIG_DOWN.value
        else:
            code = Action.DIG.value
        result = await self.execute(code)
        return result == "true"

    async def place(self, direction: str, block: str = None, text: str = None) -> bool:
        direction = direction.upper()
        text_str = f', text="{text}"' if text else ""
        if direction == "UP":
            code = Action.PLACE_UP.value.format(text=text_str)
        elif direction == "DOWN":
            code = Action.PLACE_DOWN.value.format(text=text_str)
        else:
            code = Action.PLACE.value.format(text=text_str)
        result = await self.execute(code)
        return result == "true"

    async def attack(self, direction: str) -> bool:
        direction = direction.upper()
        if direction == "UP":
            code = Action.ATTACK_UP.value
        elif direction == "DOWN":
            code = Action.ATTACK_DOWN.value
        else:
            code = Action.ATTACK.value
        result = await self.execute(code)
        return result == "true"

    async def select_slot(self, slot: int):
        code = InventoryOp.SELECT.value.format(slot=slot)
        await self.execute(code)

    async def craft(self, limit: int = 64) -> bool:
        code = CraftOp.CRAFT.value.format(limit=limit)
        result = await self.execute(code)
        return result == "true"

    async def transfer_to(self, target: int, count: int = None) -> bool:
        count_str = str(count) if count is not None else ""
        code = InventoryOp.TRANSFER_TO.value.format(target=target, count=count_str)
        result = await self.execute(code)
        return result == "true"

    async def drop(self, direction: str = "forward", count: int = None) -> bool:
        direction = direction.upper()
        count_str = str(count) if count is not None else ""
        if direction == "UP":
            code = DropOp.DROP_UP.value.format(count=count_str)
        elif direction == "DOWN":
            code = DropOp.DROP_DOWN.value.format(count=count_str)
        else:
            code = DropOp.DROP.value.format(count=count_str)
        result = await self.execute(code)
        return result == "true"

    async def suck(self, direction: str = "forward", count: int = None) -> bool:
        direction = direction.upper()
        count_str = str(count) if count is not None else ""
        if direction == "UP":
            code = SuckOp.SUCK_UP.value.format(count=count_str)
        elif direction == "DOWN":
            code = SuckOp.SUCK_DOWN.value.format(count=count_str)
        else:
            code = SuckOp.SUCK.value.format(count=count_str)
        result = await self.execute(code)
        return result == "true"

    async def refuel(self, count: int = None) -> bool:
        count_str = str(count) if count is not None else ""
        code = FuelOp.REFUEL.value.format(count=count_str)
        result = await self.execute(code)
        return result == "true"

    async def equip_left(self) -> bool:
        code = EquipmentOp.EQUIP_LEFT.value
        result = await self.execute(code)
        return result == "true"

    async def equip_right(self) -> bool:
        code = EquipmentOp.EQUIP_RIGHT.value
        result = await self.execute(code)
        return result == "true"

    async def get_inventory_state(self):
        selected = await self.execute(InventoryOp.SELECTED_SLOT.value)
        slots = []
        for i in range(1, 17):
            raw = await self.execute(InventoryOp.ITEM_DETAIL.value.format(slot=i))
            if raw and raw != "null":
                try:
                    detail = json.loads(raw)
                    slots.append({
                        "slot": i,
                        "name": detail.get("name", "unknown"),
                        "count": detail.get("count", 0),
                        "detail": detail,
                    })
                except json.JSONDecodeError:
                    slots.append({"slot": i, "name": "unknown", "count": 0})
            else:
                slots.append({"slot": i, "name": None, "count": 0})
        fuel_level_raw = await self.execute(FuelOp.LEVEL.value)
        fuel_limit_raw = await self.execute(FuelOp.LIMIT.value)
        try:
            fuel_level = int(fuel_level_raw.strip()) if fuel_level_raw.strip() else 0
        except ValueError:
            fuel_level = 0
        try:
            fuel_limit = int(fuel_limit_raw.strip()) if fuel_limit_raw.strip() else 0
        except ValueError:
            fuel_limit = 0
        return {
            "selected_slot": int(selected.strip()) if selected.strip() else 1,
            "slots": slots,
            "fuel": {"level": fuel_level, "limit": fuel_limit},
        }

    async def start(self):
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        async def server(ws, path=None):
            conn = TurtleConnection("turtle", ws)
            self.turtles[conn.id] = conn
            self._current_turtle_id = conn.id
            try:
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        await ws.send(json.dumps({"error": "invalid JSON"}))
                        continue
                    if data.get("type") == "register":
                        conn.id = data.get("id", conn.id)
                    elif data.get("type") == "position":
                        conn.x = data.get("x", conn.x)
                        conn.y = data.get("y", conn.y)
                        conn.z = data.get("z", conn.z)
                        conn.facing = data.get("facing", conn.facing)
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                conn.connected = False
                if self._current_turtle_id == conn.id:
                    self._current_turtle_id = None
        try:
            async with websockets.serve(server, "0.0.0.0", 3000):
                await asyncio.Future()
        except OSError as e:
            print(f"WebSocket server error: {e}")

    async def _dispatch_loop(self):
        while True:
            if self.pending and self._current and self._current.connected:
                async with self.lock:
                    if self.pending:
                        code = self.pending.pop(0)
                        await self._current.send(json.dumps({"code": code}))
            await asyncio.sleep(0.5)
