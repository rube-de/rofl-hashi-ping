#!/usr/bin/env python3

import argparse
import asyncio
from src.rofl_oracle.header_oracle import HeaderOracle


async def main():
    """
    Main method for the Python CLI tool.

    :return: None
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ROFL Header Oracle")
    parser.add_argument(
        "--local",
        action="store_true",
        default=False,
        help="Run in local mode without ROFL utilities (for testing)"
    )
    args = parser.parse_args()
    
    if args.local:
        print("=== ROFL Header Oracle Starting (LOCAL MODE) ===")
        print("Local mode enabled: ROFL utilities disabled")
    else:
        print("=== ROFL Header Oracle Starting ===")
        
    print("Creating HeaderOracle instance...")
    
    try:
        headerOracle = HeaderOracle(local_mode=args.local)
        print("HeaderOracle instance created, starting main loop...")
        await headerOracle.run()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
