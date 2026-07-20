# Study Roadmap

You're starting from near-zero on CXL. This is the order to read things in. Budget ~2 focused days
to get to "I can explain this to the prof without hedging."

## Reading order

| # | File | What you get | Time |
|---|------|--------------|------|
| 1 | [01-cxl-basics.md](01-cxl-basics.md) | What CXL is, why a memory expander is slow | 45 min |
| 2 | [02-memory-tiering-fundamentals.md](02-memory-tiering-fundamentals.md) | Hot/cold pages, promotion/demotion, the Linux machinery | 45 min |
| 3 | [03-the-core-problem.md](03-the-core-problem.md) | **The thing you're actually replicating.** Read twice. | 60 min |
| 4 | [04-paper-memstrata.md](04-paper-memstrata.md) | HW tiering + multi-tenant interference | 30 min |
| 5 | [05-paper-m5.md](05-paper-m5.md) | Sub-page (64B) tracking — closest to your instinct | 30 min |
| 6 | [06-paper-neomem.md](06-paper-neomem.md) | Profiling in the CXL controller | 30 min |
| 7 | [07-cxlramsim.md](07-cxlramsim.md) | The simulator, and where your code hooks in | 45 min |
| 8 | [08-glossary.md](08-glossary.md) | Keep open in a tab while reading everything else | — |

## The one-paragraph version

CXL lets you hang extra DRAM off the PCIe bus. It's cheap capacity but ~2–3× the latency of local
DDR. So you get a two-tier memory system, and something has to decide which data lives in fast local
DRAM and which lives in slow CXL memory. Today that "something" is the OS, working in 4 KB pages,
using profiling mechanisms that are either too coarse, too slow, or too expensive. All three papers
attack this, from different angles. Your job is to reproduce the *problem* in CXLRAMSim first, then
(optionally) one of the *solutions*.

## Before you meet the prof, be able to answer

1. Why is a 4 KB page the wrong unit for tiering? (Give two distinct reasons — see 03.)
2. What does the OS actually pay to migrate one page? (Name four costs.)
3. Why can't we just profile every access in software?
4. What does hardware-managed tiering (Intel Flat Memory Mode) do differently, and what new problem
   does it create?
5. Which of the three papers are you doing, and what specifically would you build in the simulator?

## A correction to flag early

Your framing was "moving pages from slow to fast isn't cutting it, we should do lines instead."
That's *half* right and it's worth getting precise, because the prof will push on it — see
[03-the-core-problem.md](03-the-core-problem.md#is-cacheline-granularity-actually-the-answer).
Short version: granularity is one of three separate problems, and the papers disagree about whether
it's the most important one.
