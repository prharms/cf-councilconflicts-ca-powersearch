#!/usr/bin/env python3
"""
Compatibility wrapper for political conflict analysis.

This script provides backward compatibility by importing from the new package structure.
Use 'python -m political_conflict_analysis' or the 'political-conflict-analysis' command instead.
"""

import sys
import warnings

# Show deprecation warning
warnings.warn(
    "Using scripts/compare_beneficiaries.py is deprecated. "
    "Use 'python -m political_conflict_analysis' or the 'political-conflict-analysis' command instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import and run the main function from the package
try:
    from political_conflict_analysis import main
    main()
except ImportError as e:
    print(f"Error importing political_conflict_analysis: {e}")
    print("Please install the package first: pip install -e .")
    sys.exit(1) 