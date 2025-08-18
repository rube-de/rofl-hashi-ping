# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen

# Copy source code
COPY main.py ./
COPY src/ ./src/

# Set environment variables (can be overridden by compose.yaml)
ENV SOURCE_RPC_URL=https://ethereum.publicnode.com
ENV POLLING_INTERVAL=12
ENV NETWORK=sapphire-testnet
ENV CONTRACT_ADDRESS=""

# Run the oracle
CMD ["uv", "run", "python", "main.py"]
