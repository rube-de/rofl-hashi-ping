#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
import sys

# Configure logging before any other imports create loggers
def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# Get logger for this module
logger = logging.getLogger(__name__)

from src.rofl_oracle.config import OracleConfig
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
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)"
    )
    args = parser.parse_args()
    
    # Set up logging with specified level
    setup_logging(args.log_level)
    
    if args.local:
        logger.info("=== ROFL Header Oracle Starting (LOCAL MODE) ===")
        logger.info("Local mode enabled: ROFL utilities disabled")
    else:
        logger.info("=== ROFL Header Oracle Starting ===")
        
    logger.info("Loading configuration from environment...")
    
    try:
        # Load configuration from environment
        config = OracleConfig.from_env(local_mode=args.local)
        logger.info("Configuration loaded successfully")
        
        logger.info("Creating HeaderOracle instance...")
        headerOracle = HeaderOracle(config)
        logger.info("HeaderOracle instance created, starting main loop...")
        await headerOracle.run()
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        logger.error("Please check your environment variables:")
        logger.error("  - SOURCE_RPC_URL: RPC endpoint for source chain")
        logger.error("  - SOURCE_CONTRACT_ADDRESS: BlockHeaderRequester contract address")
        logger.error("  - CONTRACT_ADDRESS: ROFLAdapter contract on Sapphire")
        logger.error("  - NETWORK: Target network (default: sapphire-testnet)")
        logger.error("  - POLLING_INTERVAL: Event polling interval (default: 12)")
        if args.local:
            logger.error("  - LOCAL_PRIVATE_KEY: Required for local mode")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
