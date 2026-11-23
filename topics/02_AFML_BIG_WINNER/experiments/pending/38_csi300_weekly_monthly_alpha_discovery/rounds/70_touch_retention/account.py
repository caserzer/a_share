from pathlib import Path
import sys
from importlib.util import spec_from_file_location,module_from_spec
here=Path(__file__).resolve().parent
spec=spec_from_file_location("mature_group_account",here.parent/"64_mature_group_switch/account.py")
engine=module_from_spec(spec);spec.loader.exec_module(engine)
engine.run_scope(sys.argv[1],here/"results")
