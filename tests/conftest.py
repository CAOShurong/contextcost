"""Make ``src/`` importable without installing anything first.

CI sets ``PYTHONPATH: src`` and that is the documented way to run the suite.
This file exists for every other case: a contributor who types ``pytest`` in a
fresh clone, and -- the reason it was actually written -- an unattended session
that runs the tests with no environment set up and would otherwise report a
collection error as if the code were broken.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))
