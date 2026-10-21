"""Rebuild v5 prices/labels with frozen source, no network or live workspace reads."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from archive import sha, utc_now, write_json
from v5_core import V5, PUBLIC


def main():
    release = Path(json.loads((PUBLIC / "release.json").read_text())["path"])
    replay = V5 / "replay" / utc_now().replace(":", "").replace(".", "")
    replay.mkdir(parents=True)
    for name in ["inputs", "raw", "acquired", "baseline_catalog"]:
        shutil.copytree(release / name, replay / name)
    shutil.copyfile(release / "legacy_qfq_inputs.json", replay / "legacy_qfq_inputs.json")
    output = replay / "provenance"
    output.mkdir()
    guard = replay / "guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import os,sys,socket\n"
        "def deny_network(*args,**kwargs): raise RuntimeError('offline replay network disabled')\n"
        "socket.socket.connect=deny_network\n"
        "socket.socket.connect_ex=deny_network\n"
        "socket.create_connection=deny_network\n"
        f"allowed=({str(replay)!r}, {str(release / 'source')!r})\n"
        "blocked=('/home/xiaolv/code/a_share/', '/home/xiaolv/.cache/a_share/ep30_d2/')\n"
        "def audit(event,args):\n"
        " if event not in ('open','os.listdir','os.scandir') or not args: return\n"
        " p=args[0]\n"
        " if not isinstance(p,(str,bytes,os.PathLike)): return\n"
        " p=os.path.abspath(os.fsdecode(p))\n"
        " if any(p.startswith(x) for x in blocked) and not any(p==x or p.startswith(x+'/') for x in allowed):\n"
        "  raise RuntimeError('live workspace/cache access denied: '+p)\n"
        "sys.addaudithook(audit)\n"
    )
    env = dict(os.environ, EP30_V5_ROOT=str(replay), EP30_V5_PUBLIC=str(output), EP30_V5_OFFLINE="1",
               PYTHONPATH=str(guard)+os.pathsep+str(release / "source/src"), PYTHONDONTWRITEBYTECODE="1")
    logs = {}
    for name in ["v5_prices.py", "v5_labels.py", "v5_qualify.py"]:
        log = replay / (name + ".log")
        with log.open("w") as handle:
            subprocess.run([sys.executable, str(release / "source/src" / name)], env=env, cwd=replay,
                           stdout=handle, stderr=subprocess.STDOUT, check=True)
        logs[name] = sha(log)
        print("replay script complete", name, flush=True)
    n = rows = 0
    for reference in sorted((release / "normalized").rglob("*.parquet")):
        relative = reference.relative_to(release)
        a, b = pd.read_parquet(reference), pd.read_parquet(replay / relative)
        pd.testing.assert_frame_equal(a, b)
        n += 1
        rows += len(a)
    for name in ["price_adjustment_coverage.csv", "code_factor_scale_links.csv", "legacy_qfq_comparison.csv", "label_coverage.csv", "label_status_totals.csv", "legacy_qfq_method_audit.csv", "qfq_provider_sensitivity.csv"]:
        assert sha(release / "provenance" / name) == sha(output / name), name
    result = dict(status="PASS", release_id=release.name, network_disabled=True, live_workspace_and_cache_reads_denied=True,
                  used_frozen_source=True, all_columns_compared=True, parquet_products=n, rows_compared=rows,
                  audit_csv_files_byte_equal=7, log_sha256=logs, replay_path=str(replay))
    write_json(PUBLIC / "frozen_code_replay.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
