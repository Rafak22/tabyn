"""
تبيَّن — Knowledge Base Builder
Runs all collectors in sequence to build the complete KB.

Usage:
    python run_kb.py              # full build (all collectors)
    python run_kb.py --trusted    # only trusted sources (daily update)
    python run_kb.py --eval       # only evaluation set
    python run_kb.py --benchmarks # only benchmarks
    python run_kb.py --fresh      # full rebuild from scratch (no merge)
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from collectors.trusted_sources import run as run_trusted
from collectors.evaluation_set  import run as run_eval
from collectors.benchmarks      import run as run_benchmarks


def print_banner():
    print("""
╔══════════════════════════════════════════════════════╗
║                                                      ║
║           تبيَّن — Knowledge Base Builder            ║
║                                                      ║
║   Room 1: Trusted Sources  (واس, العربية, الجزيرة)  ║
║   Room 2: Evaluation Set   (Misbar, Fatabyyano)      ║
║   Room 3: Benchmarks       (AVeriTeC, AFND, FACTors) ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """)


def main():
    print_banner()

    args = sys.argv[1:]
    fresh = "--fresh" in args
    incremental = not fresh

    if not args or "--fresh" in args:
        # Run everything
        run_trusted(incremental=incremental)
        run_eval(incremental=incremental)
        run_benchmarks()

    elif "--trusted" in args:
        run_trusted(incremental=incremental)

    elif "--eval" in args:
        run_eval(incremental=incremental)

    elif "--benchmarks" in args:
        run_benchmarks()

    print("""
╔══════════════════════════════════════════════════════╗
║  ✅  Knowledge Base build complete!                  ║
║                                                      ║
║  Output files:                                       ║
║  • data/trusted_sources/trusted_articles.json        ║
║  • data/evaluation_set/evaluation_claims.json        ║
║  • data/benchmarks/averitec.json                     ║
║                                                      ║
║  Next step: load into vector DB (ChromaDB / FAISS)   ║
╚══════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
