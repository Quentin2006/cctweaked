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


class Action(Enum):
    DIG = "local ok = turtle.dig(); return tostring(ok)"
    DIG_UP = "local ok = turtle.digUp(); return tostring(ok)"
    DIG_DOWN = "local ok = turtle.digDown(); return tostring(ok)"
    PLACE = "local ok = turtle.place({text}); return tostring(ok)"
    PLACE_UP = "local ok = turtle.placeUp({text}); return tostring(ok)"
    PLACE_DOWN = "local ok = turtle.placeDown({text}); return tostring(ok)"
    ATTACK = "local ok = turtle.attack(); return tostring(ok)"
    ATTACK_UP = "local ok = turtle.attackUp(); return tostring(ok)"
    ATTACK_DOWN = "local ok = turtle.attackDown(); return tostring(ok)"


class Sense(Enum):
    DETECT = "local ok = turtle.detect(); return tostring(ok)"
    DETECT_UP = "local ok = turtle.detectUp(); return tostring(ok)"
    DETECT_DOWN = "local ok = turtle.detectDown(); return tostring(ok)"
    COMPARE = "local ok = turtle.compare(); return tostring(ok)"
    COMPARE_UP = "local ok = turtle.compareUp(); return tostring(ok)"
    COMPARE_DOWN = "local ok = turtle.compareDown(); return tostring(ok)"
    COMPARE_TO = "local ok = turtle.compareTo({slot}); return tostring(ok)"


class InventoryOp(Enum):
    ITEM_COUNT = "return tostring(turtle.getItemCount({slot}))"
    ITEM_SPACE = "return tostring(turtle.getItemSpace({slot}))"
    ITEM_DETAIL = (
        "local d = turtle.getItemDetail({slot}); "
        "if d then return textutils.serializeJSON(d) else return 'null' end"
    )
    SELECTED_SLOT = "return tostring(turtle.getSelectedSlot())"
    SELECT = "turtle.select({slot}); return 'true'"
    TRANSFER_TO = "local ok = turtle.transferTo({target}{count}); return tostring(ok)"


class DropOp(Enum):
    DROP = "local ok = turtle.drop({count}); return tostring(ok)"
    DROP_UP = "local ok = turtle.dropUp({count}); return tostring(ok)"
    DROP_DOWN = "local ok = turtle.dropDown({count}); return tostring(ok)"


class SuckOp(Enum):
    SUCK = "local ok = turtle.suck({count}); return tostring(ok)"
    SUCK_UP = "local ok = turtle.suckUp({count}); return tostring(ok)"
    SUCK_DOWN = "local ok = turtle.suckDown({count}); return tostring(ok)"


class FuelOp(Enum):
    LEVEL = "return tostring(turtle.getFuelLevel())"
    LIMIT = "return tostring(turtle.getFuelLimit())"
    REFUEL = "local ok = turtle.refuel({count}); return tostring(ok)"


class EquipmentOp(Enum):
    EQUIP_LEFT = "local ok = turtle.equipLeft(); return tostring(ok)"
    EQUIP_RIGHT = "local ok = turtle.equipRight(); return tostring(ok)"
    GET_LEFT = (
        "local d = turtle.getEquippedLeft(); "
        "if d then return textutils.serializeJSON(d) else return 'null' end"
    )
    GET_RIGHT = (
        "local d = turtle.getEquippedRight(); "
        "if d then return textutils.serializeJSON(d) else return 'null' end"
    )


class CraftOp(Enum):
    CRAFT = "local ok = turtle.craft({limit}); return tostring(ok)"


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
            if self.commands and self.ws is not None:
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
        if self.ws is None:
            raise ConnectionError("Turtle not connected")
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

    async def dig(self, direction: str) -> bool:
        d = direction.upper()
        if d == "UP":
            code = Action.DIG_UP.value
        elif d == "DOWN":
            code = Action.DIG_DOWN.value
        else:
            code = Action.DIG.value
        result = await self.execute(code)
        ok = result.get("result") == "true"
        if ok:
            pos = self._get_block_pos(direction)
            self._remove_block(pos)
        return ok

    async def place(self, direction: str, block: str | None = None,
                    text: str | None = None) -> bool:
        fmt = {}
        if text:
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')
            fmt["text"] = f'"{escaped}"'
        else:
            fmt["text"] = ""
        d = direction.upper()
        if d == "UP":
            code = Action.PLACE_UP.value.format(**fmt)
        elif d == "DOWN":
            code = Action.PLACE_DOWN.value.format(**fmt)
        else:
            code = Action.PLACE.value.format(**fmt)
        result = await self.execute(code)
        ok = result.get("result") == "true"
        if ok and block:
            pos = self._get_block_pos(direction)
            self._save_block(pos, block)
        return ok

    async def attack(self, direction: str) -> bool:
        d = direction.upper()
        if d == "UP":
            code = Action.ATTACK_UP.value
        elif d == "DOWN":
            code = Action.ATTACK_DOWN.value
        else:
            code = Action.ATTACK.value
        result = await self.execute(code)
        return result.get("result") == "true"

    def _remove_block(self, pos: tuple[int, int, int]) -> None:
        x, y, z = pos
        lines: list[str] = []
        try:
            with open(self.blocks_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",", 3)
                    if (len(parts) == 4 and int(parts[0]) == x
                            and int(parts[1]) == y and int(parts[2]) == z):
                        continue  # skip this line = remove
                    lines.append(line)
        except FileNotFoundError:
            return
        with open(self.blocks_file, "w") as f:
            f.write("\n".join(lines) + "\n" if lines else "")

    async def detect_block(self, direction: str) -> bool:
        d = direction.upper()
        if d == "UP":
            code = Sense.DETECT_UP.value
        elif d == "DOWN":
            code = Sense.DETECT_DOWN.value
        else:
            code = Sense.DETECT.value
        result = await self.execute(code)
        return result.get("result") == "true"

    async def compare_block(self, direction: str) -> bool:
        d = direction.upper()
        if d == "UP":
            code = Sense.COMPARE_UP.value
        elif d == "DOWN":
            code = Sense.COMPARE_DOWN.value
        else:
            code = Sense.COMPARE.value
        result = await self.execute(code)
        return result.get("result") == "true"

    async def compare_to(self, slot: int) -> bool:
        code = Sense.COMPARE_TO.value.format(slot=slot)
        result = await self.execute(code)
        return result.get("result") == "true"

    async def get_item_count(self, slot: int | None = None) -> int:
        code = InventoryOp.ITEM_COUNT.value.format(
            slot=slot if slot is not None else "")
        result = await self.execute(code)
        raw = result.get("result", "0")
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0

    async def get_item_space(self, slot: int | None = None) -> int:
        code = InventoryOp.ITEM_SPACE.value.format(
            slot=slot if slot is not None else "")
        result = await self.execute(code)
        raw = result.get("result", "0")
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0

    async def get_item_detail(self, slot: int | None = None,
                              detailed: bool = False) -> dict | None:
        op = InventoryOp.ITEM_DETAIL  # TODO: support detailed
        code = op.value.format(slot=slot if slot is not None else "")
        result = await self.execute(code)
        raw = result.get("result")
        if raw == "null" or raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def get_selected_slot(self) -> int:
        result = await self.execute(InventoryOp.SELECTED_SLOT.value)
        raw = result.get("result", "1")
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 1

    async def select_slot(self, slot: int) -> bool:
        code = InventoryOp.SELECT.value.format(slot=slot)
        await self.execute(code)
        return True

    async def transfer_to(self, slot: int,
                          count: int | None = None) -> bool:
        count_str = f", {count}" if count is not None else ""
        code = InventoryOp.TRANSFER_TO.value.format(
            target=slot, count=count_str)
        result = await self.execute(code)
        return result.get("result") == "true"

    async def drop(self, direction: str,
                   count: int | None = None) -> bool:
        d = direction.upper()
        count_str = count if count is not None else ""
        if d == "UP":
            code = DropOp.DROP_UP.value.format(count=count_str)
        elif d == "DOWN":
            code = DropOp.DROP_DOWN.value.format(count=count_str)
        else:
            code = DropOp.DROP.value.format(count=count_str)
        result = await self.execute(code)
        return result.get("result") == "true"

    async def suck(self, direction: str,
                   count: int | None = None) -> bool:
        d = direction.upper()
        count_str = count if count is not None else ""
        if d == "UP":
            code = SuckOp.SUCK_UP.value.format(count=count_str)
        elif d == "DOWN":
            code = SuckOp.SUCK_DOWN.value.format(count=count_str)
        else:
            code = SuckOp.SUCK.value.format(count=count_str)
        result = await self.execute(code)
        return result.get("result") == "true"

    async def get_fuel_level(self) -> int | str:
        result = await self.execute(FuelOp.LEVEL.value)
        raw = result.get("result", "0")
        if raw == "unlimited":
            return raw
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0

    async def get_fuel_limit(self) -> int | str:
        result = await self.execute(FuelOp.LIMIT.value)
        raw = result.get("result", "0")
        if raw == "unlimited":
            return raw
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0

    async def refuel(self, count: int | None = None) -> bool:
        count_str = count if count is not None else ""
        code = FuelOp.REFUEL.value.format(count=count_str)
        result = await self.execute(code)
        return result.get("result") == "true"

    async def equip_left(self) -> bool:
        result = await self.execute(EquipmentOp.EQUIP_LEFT.value)
        return result.get("result") == "true"

    async def equip_right(self) -> bool:
        result = await self.execute(EquipmentOp.EQUIP_RIGHT.value)
        return result.get("result") == "true"

    async def get_equipped_left(self) -> dict | None:
        result = await self.execute(EquipmentOp.GET_LEFT.value)
        raw = result.get("result")
        if raw == "null" or raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def get_equipped_right(self) -> dict | None:
        result = await self.execute(EquipmentOp.GET_RIGHT.value)
        raw = result.get("result")
        if raw == "null" or raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def craft(self, limit: int = 64) -> bool:
        code = CraftOp.CRAFT.value.format(limit=limit)
        result = await self.execute(code)
        return result.get("result") == "true"

    async def get_inventory_state(self) -> dict:
        slots = []
        for slot in range(1, 17):
            detail = await self.get_item_detail(slot)
            slots.append(detail)
        selected = await self.get_selected_slot()
        fuel_level = await self.get_fuel_level()
        fuel_limit = await self.get_fuel_limit()
        return {
            "selected_slot": selected,
            "slots": slots,
            "fuel": {"level": fuel_level, "limit": fuel_limit},
        }

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
