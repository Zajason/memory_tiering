# Figure 4 clarification request (draft, not sent)

Subject: M5 Figure 4 reproduction: input datasets and WAC collection procedure

Dear M5 authors,

I am an NTUA student working on a memory-tiering project with CSLab. I am trying
to reproduce the page-sparsity distributions in Figure 4 of your ASPLOS 2025
paper, and also compare them with unfiltered application accesses.

I have implemented a Pin profiler that records distinct 64B lines per 4KB page,
with a software cache model for the memory-traffic measurement. I understand
this is an approximation, not a replacement for your CXL-device measurements.

I found the benchmark commands in the public artifact, but the dataset download
location in `testing_scripts/README.md` appears to be blank. Could you share:

1. The reduced graph inputs (`twitter_reduced_6G.sg`,
   `direct_social_structure.wel`, and `direct_social_structure_3-5G.wel`), or the
   preprocessing commands, including vertex ordering and SSSP edge weights?
2. The Figure 4 measurement procedure: when WAC collection starts/stops, how
   often counters reset or regions rotate, and how multiple samples are combined?
3. The page population used in the CDF: only pages with a recorded request, all
   allocated pages, or another selection? Does collection include initialization,
   kernel traffic, and both reads and writebacks?
4. Whether Figure 4 uses the same benchmark revisions, thread/trial counts and
   LLC partition as the published evaluation commands? Table 3 lists 10 LLC ways
   for GAPBS, while the artifact's mask `0x7FC0` enables nine.

I can share our code and the controlled comparisons. I would like to resolve
these details before attributing disagreement to hardware/model differences or
choosing a collection window.

Thank you for your time,
Iason Zakynthinos

## Search record (2026-10-18)

- Official artifact main revision remains
  `d3d90d9308a4abd3af70e99c81d4ed8d445320cf`.
- The public API lists one branch (`main`), no releases and no issues at the
  time checked. No dataset release asset or clarification thread was found.
- The complete, non-truncated `testing_scripts` listing contains Figure 8/9/10
  runners, but no named Figure 4 collection runner.
- `setup/env.sh` refers to a machine-local Memtis benchmark directory. It does
  not publish the reduced inputs or identify the precise GAPBS build revision.
- The public Google+ source archive is accessible and has been downloaded.
  Its first temporal snapshot is not the authors' reduction. Exact-filename web
  searches did not locate the reduced graph files.
- These checks establish what we found, not that no copy exists elsewhere.

Following the Memtis path did recover an upstream input source, but not the
missing reduction. Its [benchmark instructions](https://github.com/cosmoss-jigu/memtis/blob/main/memtis-userspace/bench_dir/README.md)
use upstream GAPBS and a patch that only adds a `gen-twitter` make target.
[The run script](https://github.com/cosmoss-jigu/memtis/blob/main/memtis-userspace/bench_cmds/gapbs-pr.sh)
uses `twitter.sg`, not `twitter_reduced_6G.sg`.
[GAPBS's download recipe](https://github.com/sbeamer/gapbs/blob/2972aeb2703165bafd921222f4ed7196f542d3a8/benchmark/bench.mk)
points to [the KAIST Twitter release](https://github.com/ANLAB-KAIST/traces/releases/tag/twitter_rv.net).
That is a useful route for a future input-family experiment, not evidence of
M5's vertex selection, renumbering or symmetrization. No new Twitter measurement
is claimed here. The public `hehaorui/M5` fork's main branch is identical to the
official revision in this check; it adds no missing collection script.

Evidence: [artifact instructions](https://github.com/ece-fast-lab/ASPLOS-2025-M5/blob/d3d90d9308a4abd3af70e99c81d4ed8d445320cf/testing_scripts/README.md),
[environment paths](https://github.com/ece-fast-lab/ASPLOS-2025-M5/blob/d3d90d9308a4abd3af70e99c81d4ed8d445320cf/setup/env.sh),
[public releases](https://github.com/ece-fast-lab/ASPLOS-2025-M5/releases).
