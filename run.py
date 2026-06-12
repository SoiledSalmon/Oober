"""
Launcher script for the Oober JointOpt Dashboard.

This module is part of the Oober joint price-and-match
optimisation system. It launches the FastAPI development server
using uvicorn.
"""

import os
import subprocess
import sys

DEFAULT_HOST = "0.0.0.0"  # Default host address for the FastAPI backend
DEFAULT_PORT = "8000"  # Default port number for the FastAPI backend

project_root = os.path.dirname(os.path.abspath(__file__))

sys.exit(
    subprocess.call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "oober.api:app",
            "--reload",
            "--host",
            DEFAULT_HOST,
            "--port",
            DEFAULT_PORT,
        ],
        cwd=project_root,
    )
)
