"""
Streamlit Community Cloud default entrypoint proxy.
Directs execution to Home.py for GoldenCare Platform.
"""

from __future__ import annotations

import runpy
from pathlib import Path

home_file = Path(__file__).resolve().parent / "Home.py"
runpy.run_path(str(home_file), run_name="__main__")
