"""hotskew.py -- readers for the pintool's output.

Three artefacts come out of a run:

  <prefix>.summary.txt  human-readable, plus the aggregate histograms
  <prefix>.epochs.csv   one row per measurement epoch
  <prefix>.pages.bin    raw per-page records, one per (page, epoch) observation

The binary file is the interesting one. Everything the summary reports can be
recomputed from it, and it additionally supports questions the tool does not answer
directly -- most importantly restricting the population to the top-K hottest pages,
which is the population a real migration policy would actually act on.

Record layout (little-endian, packed, 160 bytes):

    uint32  epoch
    uint64  page_number          (byte address >> 12)
    uint64  reads
    uint64  writes
    uint64  touched_mask         bit w set iff 64 B word w was accessed
    uint16  word_counts[64]
"""

from __future__ import annotations

import os
import re
import struct
from dataclasses import dataclass, field

import numpy as np

WORDS_PER_PAGE = 64
PAGE_BYTES = 4096
WORD_BYTES = 64

# numpy view of one record. `<` forces little-endian and no padding.
RECORD_DTYPE = np.dtype(
    [
        ("epoch", "<u4"),
        ("page", "<u8"),
        ("reads", "<u8"),
        ("writes", "<u8"),
        ("mask", "<u8"),
        ("words", "<u2", (WORDS_PER_PAGE,)),
    ]
)

# The N values M5 plots in Figure 4, and what fraction of a page each represents.
FIG4_N = (4, 8, 16, 32, 48)
FIG4_PCT = {4: "6.25%", 8: "12.5%", 16: "25%", 32: "50%", 48: "75%"}


_POPCNT_TABLE = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def _popcount64(x: np.ndarray) -> np.ndarray:
    """Number of set bits in each element of a uint64 array."""
    if hasattr(np, "bitwise_count"):  # numpy >= 2.0
        return np.bitwise_count(x).astype(np.int32)
    # Byte-wise fallback via a 256-entry table. The input is usually a field of a
    # structured array and therefore strided, so copy before reinterpreting.
    b = np.ascontiguousarray(x).view(np.uint8).reshape(-1, 8)
    return _POPCNT_TABLE[b].sum(axis=1).astype(np.int32)


@dataclass
class Run:
    """One profiled benchmark run."""

    tag: str
    config: str = ""
    records: np.ndarray = field(default_factory=lambda: np.empty(0, RECORD_DTYPE))
    meta: dict = field(default_factory=dict)

    # -- derived quantities -------------------------------------------------

    @property
    def unique_words(self) -> np.ndarray:
        """Distinct 64 B words touched, per (page, epoch) observation."""
        return _popcount64(self.records["mask"])

    @property
    def accesses(self) -> np.ndarray:
        """DRAM accesses per (page, epoch) observation."""
        return (self.records["reads"] + self.records["writes"]).astype(np.int64)

    def figure4_cdf(self, ns=FIG4_N, top_k: int | None = None) -> dict[int, float]:
        """P(a page has at most N unique 64 B words accessed).

        This is M5's Figure 4. `top_k` restricts the population to the K hottest
        pages per epoch -- the pages a migration policy would consider. The paper
        plots the unrestricted version; the restricted one answers the question
        that actually matters for a tiering decision, and the two differ.
        """
        uw = self.unique_words
        if top_k is not None:
            uw = self._top_k_mask(top_k, uw)
        if uw.size == 0:
            return {n: float("nan") for n in ns}
        return {n: float((uw <= n).mean()) for n in ns}

    def _top_k_mask(self, top_k: int, values: np.ndarray) -> np.ndarray:
        """Select `values` for the top_k hottest pages within each epoch."""
        acc = self.accesses
        keep = []
        for e in np.unique(self.records["epoch"]):
            idx = np.flatnonzero(self.records["epoch"] == e)
            if idx.size > top_k:
                order = np.argsort(acc[idx])[::-1][:top_k]
                idx = idx[order]
            keep.append(idx)
        if not keep:
            return np.empty(0, values.dtype)
        return values[np.concatenate(keep)]

    def density(self) -> np.ndarray:
        """Fraction of each page's 64 words that were touched."""
        return self.unique_words / WORDS_PER_PAGE

    def top_word_share(self, k: int = 4) -> float:
        """Share of all accesses landing in each page's k hottest words.

        The number that makes "sparse hot page" concrete: if a page receives 500
        accesses and 480 of them hit 4 words, migrating the whole 4 KB moves 4032
        bytes nobody asked for.
        """
        w = self.records["words"].astype(np.int64)
        if w.size == 0:
            return float("nan")
        part = np.sort(w, axis=1)[:, -k:].sum()
        total = w.sum()
        return float(part / total) if total else float("nan")

    def wasted_migration_bytes(self) -> float:
        """Fraction of a migrated 4 KB page that is never touched in the window.

        Migration moves 4096 bytes. Only unique_words * 64 of them are used. This
        is the direct cost of page-granular migration under sub-page hotness.
        """
        uw = self.unique_words
        if uw.size == 0:
            return float("nan")
        return float(1.0 - uw.mean() / WORDS_PER_PAGE)


def load_pages(path: str, tag: str = "", config: str = "") -> Run:
    """Read a .pages.bin file."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    size = os.path.getsize(path)
    if size % RECORD_DTYPE.itemsize:
        raise ValueError(
            f"{path}: size {size} is not a multiple of the {RECORD_DTYPE.itemsize}-byte "
            "record; the file is truncated or was written by a different tool version"
        )
    recs = np.fromfile(path, dtype=RECORD_DTYPE)
    return Run(tag=tag or os.path.basename(path).split(".")[0], config=config, records=recs)


def load_summary(path: str) -> dict:
    """Parse the key/value part of a .summary.txt, plus its two histograms."""
    meta: dict = {}
    unique_hist = np.zeros(WORDS_PER_PAGE + 1, dtype=np.int64)
    access_hist: dict[int, int] = {}
    section = None

    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("# full unique-word histogram"):
                section = "unique"
                continue
            if line.startswith("# M5 Figure 10"):
                section = "access"
                continue
            if line.startswith("#") or not line.strip():
                continue
            if section and "," in line:
                a, b = line.split(",", 1)
                try:
                    if section == "unique":
                        unique_hist[int(a)] = int(b)
                    else:
                        access_hist[int(a)] = int(b)
                except ValueError:
                    pass
                continue
            m = re.match(r"^(\w+)\s+(.*)$", line)
            if m and section is None:
                meta[m.group(1)] = m.group(2).strip()

    meta["_unique_hist"] = unique_hist
    meta["_access_hist"] = access_hist
    return meta


def figure4_from_summary(path: str, ns=FIG4_N) -> dict[int, float]:
    """Figure 4 CDF straight from the summary file, no .pages.bin needed."""
    meta = load_summary(path)
    hist = meta["_unique_hist"]
    total = hist.sum()
    if total == 0:
        return {n: float("nan") for n in ns}
    cum = np.cumsum(hist)
    return {n: float(cum[n] / total) for n in ns}


# Values read off M5's published Figure 4, for side-by-side comparison. These are
# graph-digitised from the paper's bar chart, not from released data, so treat them
# as accurate to roughly +/-0.02.
M5_FIGURE4 = {
    "liblinear":   {4: 0.06,  8: 0.10,  16: 0.15,  32: 0.25,  48: 0.38},
    "gapbs-bc":    {4: 0.005, 8: 0.02,  16: 0.04,  32: 0.09,  48: 0.145},
    "gapbs-bfs":   {4: 0.05,  8: 0.11,  16: 0.17,  32: 0.26,  48: 0.345},
    "gapbs-cc":    {4: 0.06,  8: 0.125, 16: 0.20,  32: 0.29,  48: 0.385},
    "gapbs-pr":    {4: 0.00,  8: 0.00,  16: 0.005, 32: 0.01,  48: 0.02},
    "gapbs-sssp":  {4: 0.005, 8: 0.015, 16: 0.025, 32: 0.07,  48: 0.11},
    "gapbs-tc":    {4: 0.02,  8: 0.05,  16: 0.12,  32: 0.265, 48: 0.52},
    "cactuBSSN_r": {4: 0.005, 8: 0.01,  16: 0.025, 32: 0.045, 48: 0.075},
    "fotonik3d_r": {4: 0.005, 8: 0.09,  16: 0.095, 32: 0.11,  48: 0.12},
    "mcf_r":       {4: 0.005, 8: 0.005, 16: 0.01,  32: 0.03,  48: 0.075},
    "roms_r":      {4: 0.015, 8: 0.03,  16: 0.08,  32: 0.19,  48: 0.34},
    "cachelib":    {4: 0.56,  8: 0.70,  16: 0.74,  32: 0.795, 48: 0.855},
    "memcached":   {4: 0.38,  8: 0.60,  16: 0.755, 32: 0.86,  48: 0.965},
    "redis":       {4: 0.51,  8: 0.765, 16: 0.865, 32: 0.925, 48: 0.94},
}
