"""Entry point for the Piping Component Generator V0.1.

Usage:
    python main.py
    (equivalent to: streamlit run ui/app_streamlit.py)
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    from streamlit.web import cli as stcli

    app_path = Path(__file__).resolve().parent / "ui" / "app_streamlit.py"
    sys.argv = ["streamlit", "run", str(app_path)]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
