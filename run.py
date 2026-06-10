"""
Launcher script for the Oober JointOpt Dashboard.

Usage:
    python run.py

Starts the FastAPI server with auto-reload on port 8000.
"""

import subprocess
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))

sys.exit(
    subprocess.call(
        [
            sys.executable, "-m", "uvicorn",
            "oober.api:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000",
        ],
        cwd=project_root,
    )
)
