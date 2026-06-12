import asyncio
from TurtleManager import TurtleManager, Move


async def main():
    manager = TurtleManager()
    await manager.start()

    await manager.move(Move.UP, 5)


asyncio.run(main())
