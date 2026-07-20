# Papers

PDFs are gitignored. Download them here:

```bash
cd study/papers
curl -LO https://www.usenix.org/system/files/osdi24-zhong-yuhong.pdf   # Memstrata (OSDI'24)
curl -L -o m5-asplos25.pdf https://jiyuan.is/papers/asplos25-m5.pdf     # M5 (ASPLOS'25)
curl -L -o neomem-micro24.pdf https://arxiv.org/pdf/2403.18702          # NeoMem (MICRO'24)
curl -L -o cxlramsim.pdf https://arxiv.org/pdf/2603.29483               # CXLRAMSim v1.0
```

Also worth having, as they're the baselines the papers compare against:

- **TPP** (ASPLOS'23) — Transparent Page Placement, Meta
- **Memtis** (SOSP'23) — PEBS-driven tiering; NeoMem's strongest baseline
- **Pond** (ASPLOS'23) — CXL memory pooling in Azure; the source of the stranded-memory numbers

Artifacts:
- M5 — https://github.com/ece-fast-lab/ASPLOS-2025-M5
- NeoMem — https://github.com/PKUZHOU/NeoMem-MICRO-2024
