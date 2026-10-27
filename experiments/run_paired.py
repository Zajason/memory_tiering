#!/usr/bin/env python3
"""Run matched access/fill/traffic measurements; retain commands and completion state.

No target-curve fitting. Default: stock GAPBS, kron-23, one trial/thread, ROI only,
10M line-operand windows, cold caches at ROI, M5 Table 3's 10-way LLC capacity.
These are local experiments, not the paper's Twitter/Google/20-thread workload.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workloads", nargs="*", default=["bfs", "cc", "sssp", "bc", "pr", "tc"])
    ap.add_argument("--out", type=Path, default=ROOT / "results/paired-v2")
    ap.add_argument("--scale", type=int, default=23)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--pr-iterations", type=int)
    ap.add_argument("--pr-tolerance", type=float)
    ap.add_argument("--roi-epoch", type=int, choices=[0,1], default=1,
                    help="Close each trial's partial epoch (default); 0 pools across ROI calls")
    ap.add_argument("--epoch-refs", type=int, default=10)
    ap.add_argument("--epoch-traffic", type=int, default=0,
                    help="Use M modeled memory events instead of reference windows")
    ap.add_argument("--graph-prefix", type=Path,
                    help="Explicit graph prefix, with .sg / .wsg siblings")
    ap.add_argument("--graph-family", default="synthetic Kronecker")
    ap.add_argument("--llc-ways", type=int, default=10)
    ap.add_argument("--warm-setup", action="store_true")
    ap.add_argument("--max-epochs", type=int, default=0)
    ap.add_argument("--dump-pages", action="store_true")
    ap.add_argument("--gzip-pages", action="store_true", help="Stream raw records into gzip without a large intermediate file")
    ap.add_argument("--dump-max-mb", type=int, default=6144)
    ap.add_argument("--track-algo", choices=['spacesaving', 'cmsketch'])
    ap.add_argument("--track-budgets", default='50,128,512,2048,8192')
    ap.add_argument("--track-k", type=int, default=128)
    args = ap.parse_args()
    if args.gzip_pages:
        args.dump_pages = True
        args.dump_max_mb = 0
    if args.epoch_refs <= 0 or args.epoch_traffic < 0:
        ap.error("epoch-refs must be positive and epoch-traffic nonnegative")
    if args.threads <= 0 or args.trials <= 0:
        ap.error('threads and trials must be positive')
    if args.pr_iterations is not None and args.pr_iterations <= 0:
        ap.error('PageRank iteration limit must be positive')
    if args.pr_tolerance is not None and args.pr_tolerance <= 0:
        ap.error('PageRank tolerance must be positive')
    if args.graph_prefix and args.graph_family == "synthetic Kronecker":
        ap.error("explicit graphs require an explicit --graph-family")
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    pin = Path(os.environ.get("PIN_ROOT", Path.home()/"dev/advarch/pin"))/"pin"
    tool = ROOT/"src/profiler/pintool/obj-intel64/hotskew.so"
    failures = []
    input_hashes = {}
    for name in args.workloads:
        if name not in {"bfs", "cc", "sssp", "bc", "pr", "tc"}:
            ap.error(f"unsupported workload {name}")
        graph_prefix = args.graph_prefix or ROOT/f"workloads/gapbs/graphs/kron-{args.scale}"
        graph = graph_prefix.resolve().with_suffix('.wsg' if name == 'sssp' else '.sg')
        binary = ROOT/f"workloads/gapbs/{name}"
        if graph not in input_hashes:
            with graph.open('rb') as data:
                input_hashes[graph] = hashlib.file_digest(data, 'sha256').hexdigest()
        prefix = args.out/f"gapbs-{name}"
        manifest = prefix.with_suffix(".manifest.json")
        cmd = ["setarch", os.uname().machine, "-R", str(pin), "-t", str(tool),
               "-paired", "1", "-epoch_refs", str(0 if args.epoch_traffic else args.epoch_refs),
               "-epoch", str(args.epoch_traffic),
               "-max_epochs", str(args.max_epochs), "-dump_pages", str(int(args.dump_pages)),
               "-dump_max_mb", str(args.dump_max_mb), "-track", str(int(bool(args.track_algo))),
               "-l3_kb", str(4096*args.llc_ways), "-l3_assoc", str(args.llc_ways),
               "-warm_outside_roi", str(int(args.warm_setup)),
               "-roi_begin", "hotskew_roi_begin", "-roi_end", "hotskew_roi_end",
               "-roi_epoch", str(args.roi_epoch),
               "-tag", f"gapbs-{name}", "-o", str(prefix), "--", str(binary), "-f", str(graph), "-n", str(args.trials)]
        if name=='pr':
            if args.pr_iterations is not None:cmd+=['-i',str(args.pr_iterations)]
            if args.pr_tolerance is not None:cmd+=['-t',str(args.pr_tolerance)]
        if args.track_algo:
            at = cmd.index('--')
            cmd[at:at] = ['-track_algo', args.track_algo, '-track_n', args.track_budgets,
                          '-track_k', str(args.track_k), '-dump_topk', '1']
        metadata = dict(command=cmd, gzip_pages=args.gzip_pages, threads=args.threads, input=str(graph),
                        input_bytes=graph.stat().st_size,
                        input_sha256=input_hashes[graph],
                        executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                        tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),
                        graph_scale=None if args.graph_prefix else args.scale, graph_family=args.graph_family,
                        window="modeled memory events" if args.epoch_traffic else "line-operand references",
                        epoch_refs=0 if args.epoch_traffic else args.epoch_refs*1000000,
                        epoch_traffic=args.epoch_traffic*1000000,
                        roi="timed kernel", warm_setup=args.warm_setup, trials=args.trials,
                        roi_epoch=args.roi_epoch,
                        multicore_model='per-thread private caches; shared serialized LLC; no coherence',
                        status="running", started=time.time())
        if manifest.exists():
            old = json.loads(manifest.read_text())
            if (old.get("status") == "complete" and old.get("command") == cmd
                    and old.get('gzip_pages', False) == args.gzip_pages
                    and all(old.get(k) == metadata[k] for k in
                            ('tool_sha256', 'executable_sha256', 'input_sha256','threads'))):
                print(f"SKIP completed {name}", flush=True)
                continue
            raise SystemExit(f"Refusing to overwrite {manifest}; use a new --out directory")
        def save():
            temp = manifest.with_suffix(".json.tmp")
            temp.write_text(json.dumps(metadata, indent=2)+"\n")
            temp.replace(manifest)
        save()
        print(f"START {name}", flush=True)
        env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), OMP_DYNAMIC="FALSE")
        compressor = None
        guard = None
        fifo = prefix.with_suffix('.pages.bin')
        try:
            if args.gzip_pages:
                os.mkfifo(fifo)
                guard = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
                with fifo.open('rb') as src, prefix.with_suffix('.pages.bin.gz').open('wb') as dst:
                    compressor = subprocess.Popen(['gzip', '-1c'], stdin=src, stdout=dst)
            with prefix.with_suffix(".run.log").open("w") as log:
                rc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
            if guard is not None:
                os.close(guard)
                guard = None
            if compressor is not None and compressor.wait() != 0:
                raise RuntimeError('raw-record compression failed')
            summary = prefix.with_suffix(".summary.txt")
            text = summary.read_text() if summary.exists() else ""
            paired = prefix.with_suffix(".paired.csv")
            metadata.update(returncode=rc, elapsed_s=time.time()-metadata["started"],
                            status="complete" if rc == 0 and "collection_status  complete" in text
                            and paired.exists() else "limited" if rc == 0 and "collection_status  limited" in text
                            else "failed")
        except BaseException:
            metadata["status"] = "interrupted"
            save()
            raise
        finally:
            if guard is not None: os.close(guard)
            if compressor is not None:
                if compressor.poll() is None:
                    compressor.terminate()
                    compressor.wait()
                fifo.unlink(missing_ok=True)
        save()
        print(f"{metadata['status'].upper()} {name}: {metadata['elapsed_s']:.1f}s", flush=True)
        if metadata["status"] != "complete": failures.append(name)
    return bool(failures)

if __name__ == "__main__":
    raise SystemExit(main())
