"""Spouštěcí skript pro sběr dat."""
from backend.data_collector import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
