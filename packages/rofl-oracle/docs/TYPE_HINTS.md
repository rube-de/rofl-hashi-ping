# Type Hints and Modern Python Features Guide

## Python Version Requirement

This project requires **Python 3.12 or higher** to leverage modern language features including:
- Pattern matching (match/case statements)
- Union type syntax (`T | None` instead of `Optional[T]`)
- Walrus operator (`:=`)
- Improved type hints and generics

## Type Hint Conventions

### 1. Union Types (Python 3.10+)
```python
# Modern syntax (preferred)
def process(value: str | None) -> int | None:
    ...

# Legacy syntax (avoid)
from typing import Optional
def process(value: Optional[str]) -> Optional[int]:
    ...
```

### 2. Generic Collections
Always specify type parameters for collections:
```python
# Good
def get_events() -> list[dict[str, Any]]:
    ...

# Bad (too vague)
def get_events() -> list:
    ...
```

### 3. Return Type Annotations
All functions and methods must have return type annotations:
```python
# Correct
def setup_logging(level: str = "INFO") -> None:
    ...

async def fetch_block(number: int) -> BlockData | None:
    ...
```

### 4. Type Aliases for Complex Types
Define type aliases for complex or frequently used types:
```python
from typing import Any

# Type aliases
EventData = dict[str, Any]
ABIList = list[dict[str, Any]]
ChainId = int
```

## Modern Python Features

### 1. Pattern Matching (Python 3.10+)
Use pattern matching for cleaner conditional logic:
```python
# Pattern matching for response handling
match response:
    case {"ok": _}:
        logger.info("Success")
        return True
    case {"error": error_msg}:
        logger.error(f"Failed: {error_msg}")
        return False
    case _:
        logger.warning("Unknown response")
        return False
```

### 2. Walrus Operator (Python 3.8+)
Use the walrus operator for cleaner assignment and checks:
```python
# Good - combines assignment and check
if event := await process_event(data):
    handle_event(event)

# Instead of
event = await process_event(data)
if event:
    handle_event(event)
```

### 3. F-Strings
Always use f-strings for string formatting:
```python
# Good
logger.info(f"Processing block {block_number} from chain {chain_id}")

# Avoid
logger.info("Processing block {} from chain {}".format(block_number, chain_id))
logger.info("Processing block %d from chain %d" % (block_number, chain_id))
```

### 4. Dataclasses with Frozen and Slots
Use dataclasses for immutable data structures:
```python
@dataclass(frozen=True, slots=True)
class BlockHeaderEvent:
    chain_id: int
    block_number: int
    requester: str
    
    @property
    def unique_key(self) -> tuple[int, int, str]:
        return (self.chain_id, self.block_number, self.requester)
```

## Type Checking

### Running mypy
```bash
# Install mypy
uv add --dev mypy

# Run type checking
mypy src/

# Run with specific file
mypy src/rofl_oracle/header_oracle.py
```

### Common Type Issues and Solutions

1. **Missing imports**: Use `TYPE_CHECKING` for circular imports:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .other_module import SomeClass
```

2. **Third-party libraries**: Configure in mypy.ini:
```ini
[mypy-web3.*]
ignore_missing_imports = True
```

3. **Dynamic attributes**: Use proper type annotations:
```python
# For dynamic dict access
config: dict[str, Any] = load_config()
value: str = config.get("key", "default")
```

## Best Practices

### 1. Complete Type Coverage
- All function parameters must have type hints
- All function returns must have type hints
- Class attributes should have type annotations
- Use type hints for local variables when it improves clarity

### 2. Avoid Any When Possible
```python
# Be specific
def process_event(data: dict[str, str | int]) -> bool:
    ...

# Avoid when possible
def process_event(data: Any) -> bool:
    ...
```

### 3. Use Protocols for Duck Typing
```python
from typing import Protocol

class Submittable(Protocol):
    async def submit(self, data: bytes) -> bool:
        ...
```

### 4. Type Guards for Runtime Checks
```python
from typing import TypeGuard

def is_valid_event(data: Any) -> TypeGuard[BlockHeaderEvent]:
    return (
        isinstance(data, dict) and
        "chain_id" in data and
        "block_number" in data
    )
```

## Linting with Ruff

The project uses Ruff for linting with the following rules enabled:
- `UP` - pyupgrade (modernizes Python syntax)
- `B` - flake8-bugbear (finds likely bugs)
- `SIM` - flake8-simplify (suggests simpler code)
- `C4` - flake8-comprehensions (optimizes comprehensions)

Run linting:
```bash
ruff check src/
ruff format src/
```

## Migration Guide

### From Python 3.9 to 3.12+

1. **Update type hints**:
   - Replace `Optional[T]` with `T | None`
   - Replace `Union[A, B]` with `A | B`
   - Use `list[T]` instead of `List[T]`
   - Use `dict[K, V]` instead of `Dict[K, V]`

2. **Use pattern matching**:
   - Replace complex if/elif chains with match/case
   - Especially useful for parsing different data formats

3. **Leverage walrus operator**:
   - Combine assignment and condition checks
   - Reduce redundant function calls

4. **Modernize string operations**:
   - Use `.removeprefix()` and `.removesuffix()`
   - Always use f-strings for formatting

## Tools and Dependencies

### Development Dependencies
```toml
[dependency-groups]
dev = [
    "mypy>=1.8.0",      # Type checking
    "ruff>=0.12.8",     # Linting and formatting
    "pytest>=7.4.0",    # Testing
    "pytest-asyncio",   # Async test support
]
```

### VS Code Settings
```json
{
    "python.linting.mypyEnabled": true,
    "python.linting.enabled": true,
    "python.formatting.provider": "ruff",
    "python.analysis.typeCheckingMode": "strict"
}
```

## Resources

- [Python 3.12 What's New](https://docs.python.org/3.12/whatsnew/3.12.html)
- [PEP 604 - Union Types](https://peps.python.org/pep-0604/)
- [PEP 634 - Pattern Matching](https://peps.python.org/pep-0634/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)