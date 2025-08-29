#!/usr/bin/env python3
"""Event processing module for the ROFL Oracle.

This module handles the processing, validation, and deduplication of blockchain
events, specifically BlockHeaderRequested events from the source chain.
"""

import logging
from collections import OrderedDict
from typing import Any

from web3 import Web3

from .models import BlockHeaderEvent
from .utils.event_listener_utility import parse_event_topic_as_int

# Get logger for this module
logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes and validates blockchain events for the oracle.
    
    This class is responsible for:
    - Parsing raw event data into structured BlockHeaderEvent objects
    - Validating event structure and data
    - Filtering events by chain ID
    - Preventing duplicate event processing
    - Maintaining metrics on processed events
    """
    
    def __init__(
        self,
        source_chain_id: int,
        dedupe_window: int = 1000
    ) -> None:
        """Initialize the EventProcessor.
        
        Args:
            source_chain_id: The chain ID to filter events for
            dedupe_window: Maximum number of events to track for deduplication
        """
        self.source_chain_id = source_chain_id
        self.dedupe_window = dedupe_window
        
        # Deduplication cache using OrderedDict for O(1) lookups
        # Stores event unique keys as keys, None as values
        self.processed_events: OrderedDict[tuple[int, int, str, int], None] = OrderedDict()
        
        # Metrics tracking
        self.events_processed = 0
        self.events_filtered = 0
        self.events_duplicated = 0
        self.events_invalid = 0
        
        logger.info(
            f"EventProcessor initialized for chain {source_chain_id} "
            f"with dedupe window of {dedupe_window} events"
        )
    
    async def process_event(self, event_data: Any) -> BlockHeaderEvent | None:
        """Process a raw event into a validated BlockHeaderEvent.
        
        This method handles both dict and EventData formats from different
        event sources (WebSocket vs polling), validates the event structure,
        filters by chain ID, and checks for duplicates.
        
        Args:
            event_data: Raw event data from the event listener
            
        Returns:
            BlockHeaderEvent if valid and not duplicate, None otherwise
        """
        try:
            # Parse the raw event data
            parsed_event = self._parse_event_data(event_data)
            if not parsed_event:
                return None
            
            # Filter by chain ID
            if not self._should_process_chain(parsed_event.chain_id):
                self.events_filtered += 1
                logger.debug(
                    f"Filtered event for chain {parsed_event.chain_id} "
                    f"(configured for chain {self.source_chain_id})"
                )
                return None
            
            # Check for duplicates
            if self._is_duplicate(parsed_event):
                self.events_duplicated += 1
                logger.debug(f"Duplicate event detected: {parsed_event}")
                return None
            
            # Mark as processed
            self._mark_processed(parsed_event)
            self.events_processed += 1
            
            logger.info(f"Processed event: {parsed_event}")
            return parsed_event
            
        except Exception as e:
            self.events_invalid += 1
            logger.error(f"Error processing event: {e}", exc_info=True)
            return None
    
    def _parse_event_data(self, event_data: Any) -> BlockHeaderEvent | None:
        """Parse raw event data into a BlockHeaderEvent.
        
        Handles both dict format (from WebSocket) and EventData format
        (from polling).
        
        Args:
            event_data: Raw event data
            
        Returns:
            Parsed BlockHeaderEvent or None if parsing fails
        """
        try:
            # Extract common fields based on data format
            if hasattr(event_data, 'get'):
                # Dict format from WebSocket
                topics = event_data.get('topics', [])
                event_block = event_data.get('blockNumber', 0)
                tx_hash = event_data.get('transactionHash', '')
                log_index = event_data.get('logIndex', 0)
                data = event_data.get('data', '')
            else:
                # EventData format from polling
                topics = getattr(event_data, 'topics', [])
                # Handle case where topics is not a list
                if not isinstance(topics, list):
                    topics = list(topics) if topics else []
                event_block = getattr(event_data, 'blockNumber', 0)
                tx_hash = getattr(event_data, 'transactionHash', b'')
                if isinstance(tx_hash, bytes):
                    tx_hash = tx_hash.hex()
                else:
                    tx_hash = str(tx_hash)
                log_index = getattr(event_data, 'logIndex', 0)
                data = getattr(event_data, 'data', '')
            
            # Validate we have enough topics (signature + 2 indexed params)
            if not topics or len(topics) < 3:
                logger.warning(f"Insufficient topics in event: {len(topics) if topics else 0}")
                self.events_invalid += 1
                return None
            
            # Parse indexed parameters from topics
            chain_id = parse_event_topic_as_int(topics[1])
            requested_block = parse_event_topic_as_int(topics[2])
            
            # Parse non-indexed parameters from data
            requester, context = self._decode_event_data(data)
            
            # Normalize tx_hash format
            if isinstance(tx_hash, bytes):
                tx_hash = '0x' + tx_hash.hex()
            elif not tx_hash.startswith('0x'):
                tx_hash = '0x' + tx_hash
            
            return BlockHeaderEvent(
                chain_id=chain_id,
                block_number=requested_block,
                requester=requester,
                context=context,
                event_block_number=event_block,
                transaction_hash=tx_hash,
                log_index=log_index
            )
            
        except Exception as e:
            logger.error(f"Failed to parse event data: {e}")
            self.events_invalid += 1
            return None
    
    def _decode_event_data(self, data: str) -> tuple[str, str]:
        """Decode the non-indexed event parameters from the data field.
        
        The data field contains the ABI-encoded non-indexed parameters:
        - requester (address)
        - context (bytes32)
        
        Args:
            data: Hex-encoded event data
            
        Returns:
            Tuple of (requester_address, context_hash)
        """
        try:
            # Remove 0x prefix if present
            if data.startswith('0x'):
                data = data[2:]
            
            # Each parameter is 32 bytes (64 hex chars)
            if len(data) < 128:  # Need at least 2 parameters
                return '', ''
            
            # Extract requester address (first 32 bytes, last 20 bytes are the address)
            requester_hex = data[24:64]  # Skip 12 bytes of padding
            requester = '0x' + requester_hex
            
            # Extract context (second 32 bytes)
            context_hex = data[64:128]
            context = '0x' + context_hex
            
            # Validate and checksum the requester address
            if Web3.is_address(requester):
                requester = Web3.to_checksum_address(requester)
            
            return requester, context
            
        except Exception as e:
            logger.error(f"Failed to decode event data: {e}")
            return '', ''
    
    def _should_process_chain(self, chain_id: int) -> bool:
        """Check if an event's chain ID matches our configured chain.
        
        Args:
            chain_id: Chain ID from the event
            
        Returns:
            True if the event should be processed, False otherwise
        """
        if chain_id != self.source_chain_id:
            logger.warning(
                f"Skipping event for chain {chain_id} "
                f"(configured for chain {self.source_chain_id})"
            )
            return False
        return True
    
    def _is_duplicate(self, event: BlockHeaderEvent) -> bool:
        """Check if an event has already been processed.
        
        Uses O(1) OrderedDict lookup for efficient duplicate detection.
        
        Args:
            event: The event to check
            
        Returns:
            True if duplicate, False otherwise
        """
        # O(1) lookup in OrderedDict
        return event.unique_key in self.processed_events
    
    def _mark_processed(self, event: BlockHeaderEvent) -> None:
        """Mark an event as processed for deduplication.
        
        Uses OrderedDict with automatic eviction of oldest entries when
        the cache reaches the maximum size.
        
        Args:
            event: The event to mark as processed
        """
        event_key = event.unique_key
        
        # Check if already exists - if so, move to end (most recent)
        if event_key in self.processed_events:
            self.processed_events.move_to_end(event_key)
        else:
            # Check if at capacity and evict oldest if needed
            if len(self.processed_events) >= self.dedupe_window:
                # Remove oldest (first) item - FIFO eviction
                self.processed_events.popitem(last=False)
            
            # Add new event key (becomes most recent)
            self.processed_events[event_key] = None
    
    def get_metrics(self) -> dict[str, int]:
        """Get current processing metrics.
        
        Returns:
            Dictionary of metric names to values
        """
        return {
            "events_processed": self.events_processed,
            "events_filtered": self.events_filtered,
            "events_duplicated": self.events_duplicated,
            "events_invalid": self.events_invalid,
            "cache_size": len(self.processed_events)
        }
    
    def log_metrics(self) -> None:
        """Log current processing metrics."""
        metrics = self.get_metrics()
        logger.info(
            f"EventProcessor Metrics: "
            f"Processed={metrics['events_processed']}, "
            f"Filtered={metrics['events_filtered']}, "
            f"Duplicates={metrics['events_duplicated']}, "
            f"Invalid={metrics['events_invalid']}, "
            f"Cache={metrics['cache_size']}/{self.dedupe_window}"
        )