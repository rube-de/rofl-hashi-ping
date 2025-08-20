# ROFL Header Oracle

A Python-based Oasis ROFL (Runtime OFf-chain Logic) oracle that fetches block headers from source chains and submits them to the ROFLAdapter contract on Oasis Sapphire for cross-chain bridge verification.

## Overview

This oracle listens for `BlockHeaderRequested` events from a source chain contract and responds by fetching the requested block headers and submitting them to the Oasis Sapphire network through the ROFL runtime. It's designed to work as part of a Hashi-based cross-chain bridge system.

## Architecture

- **Source Chain**: Listens for events on any EVM-compatible blockchain
- **Target Chain**: Submits block headers to Oasis Sapphire via ROFL
- **ROFL Runtime**: Uses Oasis confidential compute for secure oracle operations
- **Event-Driven**: Processes `BlockHeaderRequested` events in real-time

## Requirements

- Docker and Docker Compose
- Access to a ROFL-enabled Oasis Network environment
- Source chain RPC endpoint
- Deployed contracts:
  - `BlockHeaderRequester` on source chain
  - `ROFLAdapter` on Oasis Sapphire

## Configuration

The oracle is configured through environment variables defined in `compose.yaml`:

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PYTHONUNBUFFERED` | Disable Python output buffering for immediate log visibility | `1` | No |
| `SOURCE_RPC_URL` | RPC endpoint for the source chain | `https://ethereum.publicnode.com` | No |
| `SOURCE_CONTRACT_ADDRESS` | Address of the BlockHeaderRequester contract on source chain | - | **Yes** |
| `NETWORK` | Target Oasis network (sapphire-testnet, sapphire-mainnet) | `sapphire-testnet` | No |
| `CONTRACT_ADDRESS` | Address of the ROFLAdapter contract on Oasis Sapphire | - | **Yes** |
| `POLLING_INTERVAL` | Seconds between event checks | `12` | No |
| `LOCAL_PRIVATE_KEY` | Private key for local testing mode | - | **Yes** (Local Mode Only) |

#### Important Notes

- **`PYTHONUNBUFFERED=1`**: Essential for real-time log visibility in containerized environments. Without this, log output may be buffered and not appear immediately, making the oracle appear "stuck" when it's actually running normally.
- **`LOCAL_PRIVATE_KEY`**: Required only when running in local mode for testing without ROFL utilities. Should be a hex-encoded private key.

## Usage

### 1. Set Environment Variables

Create a `.env` file or set environment variables:

```bash
export CONTRACT_ADDRESS=0xYourROFLAdapterAddress
export SOURCE_CONTRACT_ADDRESS=0xYourBlockHeaderRequesterAddress
export SOURCE_RPC_URL=https://your-source-chain-rpc.com
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

### 3. Monitor Logs

The oracle will display:
- Initialization progress
- ROFL connection status
- Block range being monitored  
- Event processing status
- Periodic heartbeat messages

## Local Mode (Testing)

For testing and development without ROFL infrastructure, the oracle supports a local mode that simulates transaction submissions and skips ROFL utilities.

### Local Mode Features

- **No ROFL Dependencies**: Skips ROFL utility initialization and socket connections
- **Transaction Simulation**: Logs transaction details instead of actual submission  
- **Event Listening**: Full WebSocket and polling event listening functionality
- **Local Private Key**: Uses a local private key for contract interaction testing

### Running in Local Mode

Use the dedicated local testing Docker Compose configuration:

```bash
# Run with local testing configuration
docker compose -f compose.local.yaml up --build
```

### Local Mode Environment Variables

In addition to the standard variables, local mode requires:

```bash
# Required for local mode - add this to your .env file
LOCAL_PRIVATE_KEY=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

## Operation

1. **Initialization**: Connects to ROFL runtime and source chain
2. **Event Monitoring**: Polls for `BlockHeaderRequested` events
3. **Block Fetching**: Retrieves requested block headers from source chain
4. **Header Submission**: Submits headers to Sapphire via ROFL
5. **Continuous Operation**: Runs in an infinite loop with configurable intervals

## Development

### Dependencies

- Python 3.10+
- oasis-sapphire-py
- web3.py
- httpx
- cbor2
- aiohttp

### Local Development

```bash
# Install dependencies
uv sync

# Run oracle
uv run python main.py
```

## Troubleshooting

### Oracle Appears to Hang

**Symptom**: Container shows "everything is up and running" but no further output.

**Cause**: Python output buffering in containerized environments.

**Solution**: Ensure `PYTHONUNBUFFERED=1` is set in environment variables. This forces immediate log output.

### No Events Found

**Normal Operation**: The oracle will continuously poll and show "Checking for events" messages even when no events are found. This is expected behavior.

### ROFL Connection Issues

Check that:
- `/run/rofl-appd.sock` is properly mounted
- ROFL runtime is accessible
- Contract addresses are correct

## Architecture Integration

This oracle is designed to work with:
- Hashi cross-chain message verification system
- Oasis ROFL confidential compute runtime  
- Multi-chain bridge infrastructure
- EVM-compatible source chains

## Security Considerations

- All bridge messages require multi-oracle consensus (Hashi pattern)
- ROFL provides confidential compute guarantees
- Private keys are managed by ROFL runtime
- Network communication is secured through ROFL