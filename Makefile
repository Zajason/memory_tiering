# Top-level entry points.
#
#   make build       compile the pintool and the simulator probe
#   make validate    prove the instrument measures analytic ground truth
#   make benchmarks  fetch, patch and build GAPBS / Redis / liblinear
#   make profile     run the headline profiling campaigns
#   make analyse     regenerate every derived number and figure
#   make check       verify docs/claims.md against results/
#   make reproduce   all of the above, in order, from a clean checkout
#   make determinism run the headline measurement twice and diff it
#   make site        regenerate the GitHub Pages site from results/
#
# PIN_ROOT must point at an Intel Pin installation.

PIN_ROOT    ?= $(HOME)/pin
VENV        ?= ./.venv
PY          := $(VENV)/bin/python
GRAPH_SCALE ?= 23
EPOCH_M     ?= 10

export PIN_ROOT GRAPH_SCALE EPOCH_M

.PHONY: all build validate benchmarks profile analyse check reproduce determinism site clean help

help:
	@sed -n '2,20p' $(MAKEFILE_LIST) | sed 's/^# \?//'

all: build validate

# ---------------------------------------------------------------- build
build:
	$(MAKE) -C src/profiler/pintool PIN_ROOT=$(PIN_ROOT)
	$(MAKE) -C src/sim
	gcc -O1 -g -o src/profiler/validate/synth src/profiler/validate/synth.c -lm
	gcc -O1 -g -o src/profiler/validate/kernel_blindspot src/profiler/validate/kernel_blindspot.c
	@echo "build ok"

$(PY):
	python3 -m venv $(VENV) && $(VENV)/bin/pip install -q numpy matplotlib

# ------------------------------------------------------------- validate
# Nothing downstream is meaningful if this fails, so it gates `reproduce`.
validate: build
	./src/profiler/validate/run_validation.sh $(PIN_ROOT)
	$(MAKE) -s -C src/sim test

# ------------------------------------------------------------ benchmarks
benchmarks:
	./benchmarks/setup_gapbs.sh $(GRAPH_SCALE)
	-./benchmarks/setup_redis.sh
	-./benchmarks/setup_liblinear.sh kdda

# --------------------------------------------------------------- profile
# The two GAPBS variants answer different questions (steady-state access pattern
# vs what a memory controller sees); both are needed. See report §4.2.
profile:
	./experiments/run_all_gapbs.sh both
	-./experiments/run_redis.sh spr-1t 2000000 10000000
	-./experiments/run_hotskew.sh liblinear spr-20t
	./experiments/run_trackers.sh bfs cc tc
	./experiments/sensitivity_sweep.sh all

# --------------------------------------------------------------- analyse
analyse: $(PY)
	$(PY) src/analysis/compare_to_paper.py --config spr-20t-ul
	$(PY) src/analysis/placement_study.py  --config spr-20t
	$(PY) src/analysis/latency_model.py    --config spr-20t --sensitivity \
	      --csv results/latency_spr-20t.csv
	$(PY) src/analysis/hotset_turnover.py  --config spr-20t --k 128000
	$(PY) src/analysis/granularity_sweep.py --config spr-20t-ul
	-$(PY) src/analysis/granularity_sweep.py --config spr-1t \
	      --csv results/granularity_redis.csv
	$(PY) src/analysis/plot_figures.py     --config spr-20t-ul --outdir results/figures-ul
	$(PY) src/analysis/plot_readme.py
	$(PY) src/analysis/plot_granularity.py
	$(PY) src/analysis/build_site.py

# ----------------------------------------------------------------- check
check: $(PY)
	./experiments/check_claims.sh

# ------------------------------------------------------------- reproduce
reproduce: validate benchmarks profile analyse check
	@echo
	@echo "Everything regenerated and checked against docs/claims.md."

# ------------------------------------------------------------ determinism
# ASLR made tracker runs non-deterministic and a single sample per point was read
# as an algorithmic property (report §6.1). Layout is pinned now; this demonstrates
# it rather than asserting it.
determinism: build
	@./experiments/check_determinism.sh

# ------------------------------------------------------------------ site
# docs/index.html is generated, never hand-edited. Every number on it is
# recomputed from results/ so the showcase page cannot drift from the data --
# the same rule as claims.md, for the same reason.
site: $(PY)
	$(PY) src/analysis/build_site.py
	@echo "preview: python3 -m http.server 8777 --directory docs"

clean:
	$(MAKE) -C src/profiler/pintool PIN_ROOT=$(PIN_ROOT) clean 2>/dev/null || true
	$(MAKE) -C src/sim clean
	rm -f src/profiler/validate/synth src/profiler/validate/kernel_blindspot
