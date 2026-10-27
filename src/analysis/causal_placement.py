"""Previous-window placement heuristics. These do not reproduce M5's elector.

Capacity is fixed using the first observation window, before evaluation windows.
Candidate generation cannot see the next window's pages, including when deciding
which pages have disappeared. Word-list ties are resolved by address.
"""
import numpy as np

def choose(pages, scores, capacity):
    if capacity <= 0: return set()
    valid = np.flatnonzero(scores > 0)
    order = np.lexsort((pages[valid], -scores[valid]))
    return set(int(x) for x in pages[valid[order[:capacity]]])

def candidates(prev, capacity, words_per_page=8., tracker=None):
    pages = prev['page']
    counts = (prev['reads'] + prev['writes']).astype(np.float64)
    if tracker is None:
        # Enforce a strict word budget, including at a tied threshold.
        flat = prev['words'].astype(np.int64).ravel()
        budget = min(int(np.count_nonzero(flat)), max(1, int(capacity*words_per_page)))
        pop = np.zeros(len(prev), dtype=np.float64)
        if budget:
            threshold = np.partition(flat, len(flat)-budget)[len(flat)-budget]
            selected = np.flatnonzero(flat > threshold)
            ties = np.flatnonzero(flat == threshold)
            keys = (pages[ties//64] << np.uint64(6)) | (ties % 64).astype(np.uint64)
            ties = ties[np.argsort(keys, kind='stable')[:budget-len(selected)]]
            selected = np.concatenate((selected, ties))
            pop = np.bincount(selected//64, minlength=len(prev)).astype(float)
    else:
        # A snapshot of tracker output from the previous window, never the next.
        ranks = {pg: len(tracker['hpt'])-i for i, pg in enumerate(tracker['hpt'])}
        counts = np.array([ranks.get(int(pg), 0) for pg in pages], dtype=float)
        word_counts = {}
        for word in set(tracker['hwt']):
            word_counts[word >> 6] = word_counts.get(word >> 6, 0) + 1
        pop = np.array([word_counts.get(int(pg), 0) for pg in pages], dtype=float)
    hpt = choose(pages, counts, capacity)
    eligible = np.array([int(pg) in hpt for pg in pages])
    return {'count-only': hpt,
            'hpt-driven': choose(pages, np.where(eligible, pop, 0), capacity),
            'hwt-driven': choose(pages, pop, capacity)}

def fixed_capacity(recs, fast_frac):
    if not 0 < fast_frac <= 1: raise ValueError('fast_frac must be in (0,1]')
    return max(1, int(np.count_nonzero(recs['epoch'] == recs['epoch'].min()) * fast_frac))
