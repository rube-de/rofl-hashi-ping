import logging
from typing import Any

from web3 import Web3
from web3.types import BlockData

from .block_submitter import BlockSubmitter
from .config import OracleConfig
from .event_processor import EventProcessor
from .utils.contract_utility import ContractUtility
from .utils.polling_event_listener import PollingEventListener
from .utils.rofl_utility import RoflUtility

# Get logger for this module
logger = logging.getLogger(__name__)


class HeaderOracle:
    """
    Header Oracle that fetches block headers from a source chain
    and submits them to the ROFLAdapter contract on Oasis Sapphire.
    """

    def __init__(self, config: OracleConfig) -> None:
        """
        Initialize the HeaderOracle with configuration.
        
        :param config: Oracle configuration object
        """
        self.config = config
        logger.info(f"Starting HeaderOracle initialization {'(LOCAL MODE)' if config.local_mode else ''}")
        
        try:
            # Log configuration
            self.config.log_config()

            if not config.local_mode:
                # Initialize ROFL utility and fetch secret
                logger.debug("Initializing ROFL utility...")
                self.rofl_utility = RoflUtility()
                
                logger.debug("Fetching oracle key from ROFL...")
                self.secret = self.rofl_utility.fetch_key("header-oracle")
                logger.debug("Oracle key fetched successfully")
            else:
                # Use local private key for testing
                logger.debug("Using local private key (LOCAL MODE)")
                self.secret = config.local_private_key
                self.rofl_utility = None
                logger.debug("Local private key loaded")

            # Initialize contract utility
            logger.debug("Initializing contract utility...")
            self.contract_utility = ContractUtility(config.target_chain.network, self.secret)
            logger.debug("Contract utility initialized")

            # Connect to source chain for block fetching
            logger.debug(f"Connecting to source chain at {config.source_chain.rpc_url}")
            self.source_w3 = Web3(Web3.HTTPProvider(
                config.source_chain.rpc_url, 
                request_kwargs={'timeout': config.monitoring.request_timeout}
            ))
            if not self.source_w3.is_connected():
                raise Exception(
                    f"Failed to connect to source chain at {config.source_chain.rpc_url}"
                )
            
            # Fetch chain ID from the connected RPC endpoint and update config
            logger.debug("Fetching chain ID...")
            chain_id = self.source_w3.eth.chain_id
            
            # Update config with chain ID
            self.config = self.config.with_chain_id(chain_id)
            self.source_chain_id = chain_id

            # Initialize block submitter
            logger.debug("Initializing block submitter...")
            self.block_submitter = BlockSubmitter(
                contract_util=self.contract_utility,
                rofl_util=self.rofl_utility if not config.local_mode else None,
                source_chain_id=self.source_chain_id,
                contract_address=config.target_chain.contract_address,
                request_timeout=config.monitoring.request_timeout
            )
            logger.debug("Block submitter initialized")
            
            # Initialize event processor
            logger.debug("Initializing event processor...")
            self.event_processor = EventProcessor(
                source_chain_id=self.source_chain_id,
                dedupe_window=1000  # Track last 1000 events
            )
            logger.debug("Event processor initialized")
                        
            # Load BlockHeaderRequester ABI for event listening
            logger.debug("Loading BlockHeaderRequester ABI...")
            self.block_requester_abi = self.contract_utility.get_contract_abi("BlockHeaderRequester")
            logger.debug("ABI loaded")
            
            # Initialize polling event listener
            logger.debug("Initializing polling event listener...")
            self.event_listener = PollingEventListener(
                rpc_url=config.source_chain.rpc_url,
                contract_address=config.source_chain.contract_address,
                event_name="BlockHeaderRequested",
                abi=self.block_requester_abi,
                lookback_blocks=config.monitoring.lookback_blocks
            )
            
            logger.info(f"HeaderOracle initialized ({'LOCAL' if config.local_mode else 'ROFL'} mode, source chain: {chain_id})")
            
        except Exception as e:
            logger.error(f"HeaderOracle initialization failed: {e}")
            logger.error(f"Exception type: {type(e).__name__}", exc_info=True)
            raise


    def fetch_block_by_number(self, block_number: int) -> BlockData | None:
        """
        Fetch a specific block by number from the source chain.

        :param block_number: The block number to fetch
        :return: Block data or None if fetch fails
        """
        try:
            block = self.source_w3.eth.get_block(block_number)
            return block
        except Exception as e:
            logger.error(f"Error fetching block {block_number}: {e}")
            return None
    
    async def process_block_header_event(self, event_data: Any) -> None:
        """
        Process a BlockHeaderRequested event using the EventProcessor.
        
        This method delegates event parsing, validation, and deduplication
        to the EventProcessor, then handles block fetching and submission
        for valid events.
        
        :param event_data: Event data from the event listener
        """
        try:
            # Use EventProcessor to parse, validate, and check for duplicates
            event = await self.event_processor.process_event(event_data)
            
            if not event:
                # Event was filtered, duplicate, or invalid
                return
            
            logger.info("Processing validated BlockHeaderRequested event:")
            logger.info(f"  Chain ID: {event.chain_id}")
            logger.info(f"  Requested Block: {event.block_number}")
            logger.info(f"  Requester: {event.requester}")
            logger.info(f"  Event Block: {event.event_block_number}")
            
            # Fetch the requested block
            block = self.fetch_block_by_number(event.block_number)
            
            if block:
                block_hash = block.get("hash")
                
                if block_hash is not None:
                    # Convert block_hash to hex string with 0x prefix
                    block_hash_hex = block_hash.hex() if isinstance(block_hash, bytes) else block_hash
                    if not block_hash_hex.startswith('0x'):
                        block_hash_hex = '0x' + block_hash_hex
                    
                    # Submit the block header using BlockSubmitter
                    success = await self.block_submitter.submit_block_header(event.block_number, block_hash_hex)
                    
                    if success:
                        logger.info(f"✓ Successfully submitted block {event.block_number} header to Sapphire")
                    else:
                        logger.error(f"✗ Failed to submit block {event.block_number} header")
            else:
                logger.error(f"Could not fetch block {event.block_number}")
            
            # Periodically log metrics
            if self.event_processor.events_processed % 10 == 0:
                self.event_processor.log_metrics()
                
        except Exception as e:
            logger.error(f"Error processing BlockHeaderRequested event: {e}", exc_info=True)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the oracle."""
        logger.info("Shutting down HeaderOracle...")
        await self.event_listener.stop()
        logger.info("HeaderOracle shutdown complete")

    async def run(self) -> None:
        """
        Main entry point for the HeaderOracle.
        Starts event polling using the PollingEventListener.
        """
        logger.info("Starting HeaderOracle...")
        logger.info(f"Polling for BlockHeaderRequested events from {self.config.source_chain.contract_address}")
        
        try:
            logger.info(f"Starting polling event listener with {self.config.monitoring.polling_interval} second interval...")
            
            # Start event polling (this will run indefinitely)
            await self.event_listener.start_polling(
                callback=self.process_block_header_event,
                interval=self.config.monitoring.polling_interval
            )
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            logger.info("Cleaning up...")
            await self.event_listener.stop()
            logger.info("HeaderOracle stopped")
