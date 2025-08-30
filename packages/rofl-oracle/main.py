#!/usr/bin/env python3
"""Entry point for the ROFL Header Oracle backend service.

This module provides the main entry point for the oracle service
that runs as a containerized backend in either production (ROFL)
or local testing mode.
"""

import argparse
import asyncio
import logging
import os
import sys

# Configure logging before any other imports create loggers
def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application.
    
    Args:
        level: Logging level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level: int = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# Get logger for this module
logger = logging.getLogger(__name__)

from src.rofl_oracle.config import OracleConfig
from src.rofl_oracle.header_oracle import HeaderOracle


async def main() -> None:
    """Main entry point for the ROFL Header Oracle backend service.
    
    Parses startup arguments, loads configuration from environment,
    and starts the oracle service that continuously polls for events.
    
    Raises:
        SystemExit: On configuration or runtime errors
    """
    # Parse startup arguments
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="ROFL Header Oracle Backend Service - Bridge block headers between chains",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Environment Variables:
  SOURCE_RPC_URL         - RPC endpoint for source chain
  SOURCE_CONTRACT_ADDRESS - BlockHeaderRequester contract address
  CONTRACT_ADDRESS       - ROFLAdapter contract on Sapphire
  NETWORK               - Target network (default: sapphire-testnet)
  POLLING_INTERVAL      - Event polling interval (default: 12)
  LOCAL_PRIVATE_KEY     - Private key for local mode (required with --local)
  LOG_LEVEL            - Logging level (can be overridden with --log-level)
        """
    )
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
    args: argparse.Namespace = parser.parse_args()
    
    # Set up logging with specified level
    setup_logging(args.log_level)
    
    # Use walrus operator for mode message
    if mode_msg := ("(LOCAL MODE)" if args.local else ""):
        logger.info(f"=== ROFL Header Oracle Starting {mode_msg} ===")
        logger.info("Local mode enabled: ROFL utilities disabled")
    else:
        logger.info("=== ROFL Header Oracle Starting ===")
        
    logger.info("Loading configuration from environment...")
    
    try:
        # Load configuration from environment
        config: OracleConfig = OracleConfig.from_env(local_mode=args.local)
        logger.info("Configuration loaded successfully")
        
        logger.info("Creating HeaderOracle instance...")
        header_oracle: HeaderOracle = HeaderOracle(config)
        logger.info("HeaderOracle instance created, starting main loop...")
        await header_oracle.run()
        
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
        
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal, shutting down gracefully...")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
