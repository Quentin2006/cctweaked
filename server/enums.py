"""Turtle command enums — Lua code-as-data for all turtle operations."""

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
