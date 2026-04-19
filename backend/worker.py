#!/usr/bin/env python3
"""
ARQ worker script for processing meme generation jobs.
Run with: python -m arq backend.worker.WorkerSettings
"""

from .services.worker import WorkerSettings

if __name__ == "__main__":
    import arq
    arq.run_worker(WorkerSettings)