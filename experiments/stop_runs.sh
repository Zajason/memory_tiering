#!/usr/bin/env bash
# stop_runs.sh -- reliably stop every process running the hotskew pintool.
#
# Why this is not just `pkill -f hotskew`
# --------------------------------------
# Pin replaces the injected process's command line with the *application's*, so a
# pin-controlled BFS shows up in ps as plain `bfs` with no mention of pin or of the
# tool. Matching on the command line therefore misses exactly the processes you most
# want to kill, and they keep running -- holding a core, and still appending to the
# result files a later run is trying to write.
#
# That happened during development: a PageRank run survived three separate cleanup
# attempts and spent 38 minutes writing into a result file that a subsequent run had
# already produced, silently mixing two runs into one .pages.bin.
#
# The reliable signal is the mapped library. A process running the tool has
# obj-intel64/hotskew.so mapped, and /proc/PID/maps cannot be spoofed by Pin's
# argv rewriting.
#
#   ./stop_runs.sh          list what would be killed
#   ./stop_runs.sh --kill   actually kill it

set -uo pipefail
MODE="${1:-list}"

python3 - "$MODE" <<'PY'
import os, signal, sys, glob

mode = sys.argv[1]
me = set()
p = os.getpid()
while p and p != 1:
    me.add(p)
    try:
        p = int(open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()[1])
    except Exception:
        break

targets = []
for d in glob.glob("/proc/[0-9]*"):
    pid = int(d.rsplit("/", 1)[1])
    if pid in me:
        continue
    try:
        maps = open(f"{d}/maps").read()
    except Exception:
        continue
    if "hotskew.so" not in maps:
        continue
    try:
        comm = open(f"{d}/comm").read().strip()
    except Exception:
        comm = "?"
    try:
        cwd = os.readlink(f"{d}/cwd")
    except Exception:
        cwd = "?"
    # Which result files does it hold open? That is what it would corrupt.
    outs = set()
    try:
        for fd in os.listdir(f"{d}/fd"):
            try:
                t = os.readlink(f"{d}/fd/{fd}")
            except Exception:
                continue
            if "/results/" in t:
                outs.add(os.path.basename(t).split(".")[0])
    except Exception:
        pass
    targets.append((pid, comm, cwd, sorted(outs)))

if not targets:
    print("no hotskew processes running")
    sys.exit(0)

for pid, comm, cwd, outs in targets:
    print(f"  pid {pid:<8} {comm:<12} cwd={cwd}")
    if outs:
        print(f"           writing: {', '.join(outs)}")

if mode == "--kill":
    for pid, comm, _, _ in targets:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"killed {pid} ({comm})")
        except Exception as e:
            print(f"could not kill {pid}: {e}")
else:
    print(f"\n{len(targets)} process(es). Re-run with --kill to stop them.")
PY
