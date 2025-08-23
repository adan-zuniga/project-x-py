# Installation

## Requirements

- Python 3.12 or higher
- pip or UV package manager
- TopStepX account with API access

## Install from PyPI

```bash
pip install project-x-py
```

Or using UV (recommended):

```bash
uv add project-x-py
```

## Install from Source

```bash
git clone https://github.com/TexasCoding/project-x-py.git
cd project-x-py
pip install -e .
```

## Install with Optional Features

### Real-time Features
```bash
pip install "project-x-py[realtime]"
```

### Development Tools
```bash
pip install "project-x-py[dev]"
```

### All Features
```bash
pip install "project-x-py[all]"
```

## Environment Setup

Set your API credentials as environment variables:

```bash
export PROJECT_X_API_KEY="your-api-key"  # pragma: allowlist secret
export PROJECT_X_USERNAME="your-username"
```

Or create a `.env` file:

```bash
PROJECT_X_API_KEY=your-api-key  # pragma: allowlist secret
PROJECT_X_USERNAME=your-username
```

## Verify Installation

```python
import asyncio
from project_x_py import ProjectX

async def verify():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        print(f"Connected to account: {client.account_info.name}")

asyncio.run(verify())
```

## Next Steps

- [Quick Start Guide](quickstart.md)
- [Authentication](authentication.md)
- [Configuration](configuration.md)
