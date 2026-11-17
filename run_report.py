"""Run the report tool from a source checkout without installing the GUI."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from osdagbridge.core.reports.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
