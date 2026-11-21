"""Register or start this project's Psycopg-compatible Notebook kernel.

Register with the project's interpreter: python selector_kernel.py --install
Then select "Python (agent-service / Psycopg)" in the Notebook editor.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KERNEL_NAME = "agent-service-selector"
DISPLAY_NAME = "Python (agent-service / Psycopg)"


def install() -> None:
    from jupyter_client.kernelspec import KernelSpecManager

    spec = {
        "argv": [
            sys.executable,
            str(Path(__file__).resolve()),
            "-f",
            "{connection_file}",
        ],
        "display_name": DISPLAY_NAME,
        "language": "python",
        "metadata": {"debugger": True},
    }
    with tempfile.TemporaryDirectory(prefix="selector-kernel-") as directory:
        Path(directory, "kernel.json").write_text(
            json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        destination = KernelSpecManager().install_kernel_spec(
            directory, kernel_name=KERNEL_NAME, prefix=sys.prefix
        )
    print(f"Installed {DISPLAY_NAME}: {destination}")


def launch() -> None:
    # Set the loop BEFORE ipykernel/Tornado initialize their main IOLoop.
    # Changing the policy in an already running Notebook cell is too late.
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    sys.path.insert(0, str(PROJECT_ROOT))

    from ipykernel.kernelapp import IPKernelApp

    try:
        IPKernelApp.launch_instance()
    finally:
        if not loop.is_closed():
            loop.close()


if __name__ == "__main__":
    if sys.argv[1:] == ["--install"]:
        install()
    else:
        launch()
