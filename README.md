# Business Intelligence Agent

A LangGraph-based conversational agent for business intelligence queries with TODO-based cyclic execution, natural clarification handling, and flexible data source integration.

## Overview

This agent breaks complex user requests into executable TODOs and processes them one at a time with natural pause points for clarification. Users can abort, modify, or continue at any point, making conversations flexible and transparent.

**📖 For complete flow details, see [ARCHITECTURE.md](ARCHITECTURE.md)**

## Key Features

- **Cyclic TODO Execution**: Complex requests broken into tasks, executed one at a time
- **Natural Clarification**: LLM-enabled tools can ask questions mid-execution
- **User Control**: Abort, modify, or continue TODO list at any clarification point
- **Query Metadata Caching**: Query structure saved for future data analysis
- **Memory Per TODO**: Detailed conversation history with 1 entry per TODO
- **MCP-Ready**: Tools designed for local execution now, MCP exposure later
- **Service Abstractions**: Swap LLM, embedding, and vector DB implementations

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run interactive mode
python agent.py
```

## Usage

```python
from agent import BIAgent
from config.settings import Settings

# Initialize
settings = Settings()
agent = BIAgent(settings)

# Run conversation
response = agent.run_turn("Show me shipments to Miami last week")
print(response)

# Continue conversation (memory preserved)
response = agent.run_turn("Add filter for delivered status")
print(response)

# Clear memory
agent.clear_memory()
```

## Configuration

### Environment Variables (.env)

```bash
# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Embedding
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Vector Database
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIR=./data/chroma

# Data Sources
ES_URL=http://localhost:9200
GRAPHQL_ENDPOINT=http://localhost:4000/graphql

# Agent
SHORT_TERM_MEMORY_TURNS=3
MAX_ITERATIONS=10
```

## Project Structure

```
my_cbp_agent/
├── config/                      # Settings and prompts
├── domain/                      # State, conversation, memory models
├── services/                    # LLM, embedding, vector DB abstractions
├── tools/                       # Stateless execution tools
│   ├── adapters/                # Local/MCP execution adapters
│   ├── llm/                     # LLM tool
│   ├── embedding/               # Embedding tool
│   ├── vector/                  # Vector search, field mapping
│   ├── data_sources/            # ES & GraphQL executors
│   └── query_builders/          # Query construction
├── nodes/                       # Stateful orchestration nodes
├── routing/                     # Conditional edge logic
├── memory/                      # Memory and checkpointing
├── graph.py                     # LangGraph assembly
├── agent.py                     # Main entry point
└── tests/
```

## Core Design Decisions

### 1. Separation of Concerns
- **Nodes**: Stateful orchestration (read/write state, call tools, make decisions)
- **Tools**: Stateless execution (pure input → output, no state access)

**Benefits**: Tools are unit-testable, reusable, and can be exposed via MCP

### 2. Service Abstractions
Abstract external dependencies behind interfaces:
- **LLMService**: Swap between OpenAI, Anthropic, etc.
- **VectorDBService**: Swap between ChromaDB, Redis, Qdrant
- **EmbeddingService**: Swap between OpenAI embeddings, local models

**Benefits**: Flexible implementation swapping, consistent error handling

### 3. Tool Registry
Central registry manages tool lifecycle:
- Unified interface for nodes to call tools
- Dependency injection for services
- MCP-compatible tool interface
- Adapter pattern for local vs MCP execution

**Benefits**: Easy to add new tools, ready for MCP exposure

### 4. Memory Hierarchy
Three levels of state/memory:
1. **Within-Turn State** (BIAgentState): Flows through nodes, checkpointed after turn
2. **Short-Term Memory**: Last N turns, injected as context
3. **Long-Term Memory**: All turns in vector DB (future)

**Benefits**: Clear separation, efficient context injection

### 5. Cyclic Flow
Every turn starts from `classify_intent` which checks TODO list validity:
- New request → plan new TODOs
- Exact answer → rerun same TODO
- Modification → replan TODOs
- Continue → execute next TODO

**Benefits**: Clean resumption after clarification, no nested state machines

## Example Scenarios

### Simple Query
```
User: "Show shipments to Miami last week"
Agent: Plans 5 TODOs → Executes all → Returns results
Memory: 5 entries saved
```

### With Clarification
```
User: "Show shipments to Miami last week"
Agent: "Which Miami: Port of Miami or Miami Container Terminal?"
User: "Port of Miami"
Agent: Reruns entity resolution → Continues execution → Returns results
```

### User Modifies Mid-Flow
```
User: "Show shipments to Miami last week"
Agent: "Which Miami: Port of Miami or Miami Container Terminal?"
User: "Port of Miami, but also include arrival date"
Agent: Ditches old TODO list → Replans with date field → Executes
```

### Data Analysis After Query
```
User: "Show shipments to Miami last week"
Agent: Returns results, saves query_metadata
User: "analyze delay patterns"
Agent: Retrieves query_metadata → Plans analysis TODOs → Executes
```

## Development

### Adding a New Tool

```python
# tools/custom/my_tool.py
from tools.base import BaseTool, ToolResult

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Does something useful"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string"}
            }
        }

    def execute(self, param1: str) -> ToolResult:
        result = do_something(param1)
        return ToolResult(success=True, data=result)

# Register in agent.py
self.tool_registry.register(MyTool())
```

### Adding a New Node

```python
# nodes/my_node.py
def my_node(state: BIAgentState, registry: ToolRegistry) -> dict:
    result = registry.execute("my_tool", param1="value")
    return {"my_context": {"result": result.data}}

# Add to graph.py
graph.add_node("my_node", my_node)
graph.add_edge("previous_node", "my_node")
```

## Future: MCP Exposure

Tools are designed to be exposed via MCP:

```python
# mcp_server/server.py
from tools.registry import ToolRegistry

registry = create_tool_registry(settings)
tool_defs = registry.get_mcp_definitions()
mcp_server = MCPServer(tools=tool_defs)
mcp_server.run()
```

Switch agent to use MCP tools:
```python
registry = ToolRegistry(mode="mcp")  # Instead of mode="local"
```

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Complete flow diagrams, data models, scenarios
- **[.env.example](.env.example)**: Environment variable template

## License

MIT
