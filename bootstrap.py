"""Copy default files to persistent volume on first run.

Default files live in /app/data.defaults/ (Docker) or data.defaults/
(local dev). They're copied to DATA_DIR on first startup only.
"""
import os
import shutil

DEFAULT_SRC = os.getenv(
    "DEFAULT_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "data.defaults"),
)
DATA_DIR = os.getenv("DATA_DIR", "data")
MARKER = os.path.join(DATA_DIR, ".bootstrapped")


def bootstrap():
    if not os.path.isdir(DEFAULT_SRC):
        return  # No defaults to copy
    if os.path.exists(MARKER):
        return  # Already bootstrapped

    os.makedirs(DATA_DIR, exist_ok=True)

    # Copy each item from defaults to data dir
    for item in os.listdir(DEFAULT_SRC):
        src = os.path.join(DEFAULT_SRC, item)
        dst = os.path.join(DATA_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif not os.path.exists(dst):
            shutil.copy2(src, dst)

    # Ensure subdirectories exist
    for sub in ["sessions", "memory", "opencode"]:
        os.makedirs(os.path.join(DATA_DIR, sub), exist_ok=True)

    # Write marker
    with open(MARKER, "w") as f:
        f.write("bootstrapped\n")

    # Migration: copy web/blocks.txt if it exists and volume blocks.txt doesn't
    legacy = os.path.join(os.path.dirname(__file__), "web", "blocks.txt")
    new_blocks = os.path.join(DATA_DIR, "blocks.txt")
    if os.path.isfile(legacy) and not os.path.exists(new_blocks):
        shutil.copy2(legacy, new_blocks)


if __name__ == "__main__":
    bootstrap()
