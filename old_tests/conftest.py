"""
Configuration for pytest to ensure modules can be found.
"""

import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
# This allows imports from the project root to work in tests
sys.path.insert(0, str(Path(__file__).parent.parent))
