# MIS-Zenmcp Integration

A deep integration project between MIS (Memory Integration System) and zen-MCP's 15 AI development support commands to create an AI-driven development automation system.

## Overview

This project aims to combine MIS's event-driven architecture with zen-MCP's powerful AI analysis capabilities to:
- Reduce cognitive load on developers
- Improve code quality automatically
- Provide proactive problem detection and solutions
- Gradually restore and integrate currently stopped Hooks

## Key Features

### Intelligent Event Routing
- Automatic mapping from MIS events to appropriate zen-MCP commands
- Context-aware command selection
- Priority-based execution

### 15 Integrated zen-MCP Commands
1. **chat** - General development consultation
2. **debug** - Error analysis and root cause detection
3. **planner** - Task decomposition and planning
4. **codereview** - Automated PR reviews
5. **secaudit** - Security vulnerability detection
6. **testgen** - Automatic test case generation
7. And 9 more specialized commands...

### Automated Workflows
- Error → Debug → Refactor → Test chain
- Spec change → Analyze → Consensus → Plan flow
- PR → Review → Security → Precommit pipeline

## Quick Start

### Prerequisites
- Python 3.12+
- Redis server
- PostgreSQL database
- zen-MCP API access
- MIS installation

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mis-zenmcp-integration.git
cd mis-zenmcp-integration

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Configuration

1. Configure zen-MCP API access:
```bash
export ZEN_MCP_API_KEY="your-api-key"
export ZEN_MCP_ENDPOINT="https://api.zen-mcp.com"
```

2. Configure MIS connection:
```bash
export MIS_API_ENDPOINT="http://localhost:8000"
export MIS_API_TOKEN="your-mis-token"
```

3. Set up Redis:
```bash
export REDIS_URL="redis://localhost:6379"
```

### Running the Integration

```bash
# Start the adapter service
python -m mis_zenmcp.adapter

# Or use Docker
docker-compose up -d
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  MIS Core   │────▶│  Event Bus   │────▶│  Adapter    │
└─────────────┘     └──────────────┘     └─────────────┘
       │                                          │
       ▼                                          ▼
┌─────────────┐                          ┌─────────────┐
│ Knowledge   │                          │  zen-MCP    │
│   Graph     │                          │   Commands  │
└─────────────┘                          └─────────────┘
```

## Development Status

Current Phase: **Phase 0 - Project Setup**

See [ROADMAP.md](./ROADMAP.md) for detailed implementation plan.

## Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run with coverage
pytest --cov=mis_zenmcp tests/
```

## API Documentation

### Event Subscription
```python
# Subscribe to MIS events
adapter.subscribe("file_modified", handle_file_change)
adapter.subscribe("error_detected", handle_error)
```

### Manual Command Execution
```python
# Execute zen-MCP command manually
result = await adapter.execute_command("debug", {
    "error": "TypeError: undefined is not a function",
    "context": {"file": "app.js", "line": 42}
})
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Performance Metrics

- Response time: < 2s (95th percentile)
- Error rate: < 1%
- Automation rate: 70% of development tasks
- Uptime: 99.9%

## Roadmap

- **Phase 1** (Week 1-2): Foundation and 3 core commands
- **Phase 2** (Week 3-4): Hook restoration
- **Phase 3** (Week 5-8): All 15 commands integration
- **Phase 4** (Week 9-12): Advanced automation
- **Phase 5** (Week 13-16): Optimization
- **Phase 6** (Week 17-20): ML integration

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: [docs/](./docs/)
- Issues: [GitHub Issues](https://github.com/yourusername/mis-zenmcp-integration/issues)
- Slack: #mis-zenmcp-integration

## Acknowledgments

- MIS Project Team
- zen-MCP Development Team
- All contributors