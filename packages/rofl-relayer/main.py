#!/usr/bin/env python3

import argparse
import asyncio
from src.rofl_relayer.relayer import ROFLRelayer


async def main():
    """Main entry point for the ROFL Relayer."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ROFL Relayer")
    parser.add_argument(
        "--local",
        action="store_true",
        default=False,
        help="Run in local mode without ROFL utilities"
    )
    args = parser.parse_args()
    
    if args.local:
        print("Running in LOCAL MODE")
    else:
        print("Running in ROFL MODE")
    
    # Create and run relayer
    relayer = ROFLRelayer(local_mode=args.local)
    await relayer.run()


if __name__ == "__main__":
    asyncio.run(main())