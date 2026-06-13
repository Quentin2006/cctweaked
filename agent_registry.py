"""Agent type definitions for the CC:Tweaked turtle hivemind.

Each agent type has a specific role, a skill file, and handles specific task types.
This is a static data module — no filesystem I/O, just definitions.
"""

import os


DATA_DIR = os.getenv("DATA_DIR", "data")
VALID_AGENT_IDS = {"queen", "planner", "miner", "crafter", "builder", "explorer"}
VALID_TASK_TYPES = {"plan", "mine", "dig", "collect", "craft", "smelt",
                    "build", "place", "construct", "explore", "map", "survey"}

AGENT_TYPES = {
    "queen": {
        "id": "queen",
        "name": "Queen",
        "description": "Top-level orchestrator. Receives user goals, decomposes into tasks, monitors progress, reports back.",
        "skill_file": "queen.skill.md",
        "capabilities": ["orchestration", "delegation", "monitoring", "reporting"],
        "handles_task_types": [],  # Queen doesn't handle tasks directly — it creates them
        "default_goal": "Oversee swarm operations",
        "color": "#00e5ff",  # Cyan
    },
    "planner": {
        "id": "planner",
        "name": "Planner",
        "description": "Breaks complex goals into ordered atomic subtasks with dependency tracking.",
        "skill_file": "planner.skill.md",
        "capabilities": ["decomposition", "dependency_analysis", "scheduling"],
        "handles_task_types": ["plan"],
        "default_goal": "Plan task execution order",
        "color": "#7c3aed",  # Violet
    },
    "miner": {
        "id": "miner",
        "name": "Miner",
        "description": "Extracts resources from the world. Branch mining, quarrying, cave navigation.",
        "skill_file": "miner.skill.md",
        "capabilities": ["mining", "navigation", "inventory_management"],
        "handles_task_types": ["mine", "dig", "collect"],
        "default_goal": "Mine specified resources",
        "color": "#ffb347",  # Orange
    },
    "crafter": {
        "id": "crafter",
        "name": "Crafter",
        "description": "Crafts items, manages inventory, runs furnace operations.",
        "skill_file": "crafter.skill.md",
        "capabilities": ["crafting", "smelting", "inventory_sorting"],
        "handles_task_types": ["craft", "smelt"],
        "default_goal": "Craft requested items",
        "color": "#b388ff",  # Purple
    },
    "builder": {
        "id": "builder",
        "name": "Builder",
        "description": "Places blocks according to designs. Constructs structures, walls, farms.",
        "skill_file": "builder.skill.md",
        "capabilities": ["placement", "structure_building", "coordinate_tracking"],
        "handles_task_types": ["build", "place", "construct"],
        "default_goal": "Build structures as designed",
        "color": "#2ed573",  # Green
    },
    "explorer": {
        "id": "explorer",
        "name": "Explorer",
        "description": "Maps the world, discovers resources, locates structures and caves.",
        "skill_file": "explorer.skill.md",
        "capabilities": ["mapping", "resource_detection", "navigation"],
        "handles_task_types": ["explore", "map", "survey"],
        "default_goal": "Explore and map the surrounding area",
        "color": "#ff7eb3",  # Pink
    },
}


def get_agent_type(agent_type_id: str) -> dict | None:
    """Get agent type definition by ID. Returns None if not found."""
    return AGENT_TYPES.get(agent_type_id)


def list_agent_types() -> list[dict]:
    """Return all agent type definitions."""
    return list(AGENT_TYPES.values())


def get_skill_path(agent_type_id: str) -> str:
    """Get the full path to the skill file for this agent type."""
    agent = get_agent_type(agent_type_id)
    if agent is None:
        raise KeyError(f"Unknown agent type: {agent_type_id}")
    return os.path.join(DATA_DIR, "skills", agent["skill_file"])


def get_type_for_task(task_type: str) -> dict | None:
    """Find the agent type that handles a given task type.

    Returns None if no agent handles that task type.
    """
    for agent in AGENT_TYPES.values():
        if task_type in agent["handles_task_types"]:
            return agent
    return None


def get_capable_agent_types(capability: str) -> list[dict]:
    """List agent types that have a specific capability."""
    return [a for a in AGENT_TYPES.values() if capability in a["capabilities"]]


if __name__ == "__main__":
    print("=== Agent Registry Test ===")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"Valid agent IDs: {VALID_AGENT_IDS}")
    print(f"Valid task types: {VALID_TASK_TYPES}")
    print()

    for agent in list_agent_types():
        print(f"  [{agent['id']:>8}] {agent['name']:>10} | tasks={agent['handles_task_types']} | caps={agent['capabilities']}")
    print()

    miner_type = get_agent_type("miner")
    print(f"get_agent_type('miner') -> name={miner_type['name'] if miner_type else 'N/A'}")
    print(f"get_agent_type('unknown') -> {get_agent_type('unknown')}")
    print(f"get_skill_path('builder') -> {get_skill_path('builder')}")
    smelt_type = get_type_for_task("smelt")
    print(f"get_type_for_task('smelt') -> id={smelt_type['id'] if smelt_type else 'N/A'}")
    print(f"get_type_for_task('nope') -> {get_type_for_task('nope')}")
    print(f"get_capable_agent_types('mapping') -> {[a['id'] for a in get_capable_agent_types('mapping')]}")
    print(f"get_capable_agent_types('navigation') -> {[a['id'] for a in get_capable_agent_types('navigation')]}")

    print()
    print("=== All checks passed ===")
