"""BI Agent main entry point with cyclic TODO-based execution.

Main interface for running the BI agent with the new architecture.
Handles initialization, turn execution, and memory management.
"""

from config.settings import Settings
from domain.memory import ShortTermMemory, LongTermMemory
from domain.conversation import ConversationTurn
from memory.manager import MemoryManager
from memory.checkpointer import create_checkpointer
from tools.registry import ToolRegistry
from graph import create_bi_graph

# Services
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from services.vectordb_service import create_vectordb_service

# Tools
from tools.llm.llm_tool import LLMTool
from tools.embedding.embedding_tool import EmbeddingTool
from tools.vector.vectordb_tool import VectorDBTool
from tools.vector.field_mapping_tool import FieldMappingTool
from tools.data_sources.es_executor import ESExecutorTool
from tools.data_sources.graphql_executor import GraphQLExecutorTool
from tools.query_builders.es_builder import ESQueryBuilderTool
from tools.query_builders.graphql_builder import GraphQLQueryBuilderTool


class BIAgent:
    """
    Main agent interface with cyclic TODO-based execution.

    Architecture Changes:
        - OLD: 1 user request = 1 conversation turn = 1 memory entry
        - NEW: 1 user request = N TODOs = N conversation turns = N memory entries

    Lifecycle:
        1. Initialize: Setup services, tools, graph, memory
        2. run_turn(user_input): Execute one user request
           - classify_intent → route → plan_todos → execute_next_todo (loop)
           - Save memory after EACH TODO execution
           - Return when turn ends (clarification, error, or completion)
        3. Repeat: User provides next input (answer, modification, or new request)

    Attributes:
        settings: Application settings
        llm_service: LLM service (OpenAI, Anthropic, etc.)
        embedding_service: Embedding service
        vectordb_service: Vector DB service (ChromaDB, Redis, etc.)
        short_term_memory: Last N TODO completions
        long_term_memory: All TODO completions in vector DB
        memory_manager: Memory creation and context injection
        tool_registry: Central tool registry
        graph: LangGraph compiled graph
        turn_counter: Global turn counter (increments per TODO, not per user input)

    Example Usage:
        # Initialize
        agent = BIAgent()

        # First user request
        response = agent.run_turn("Show shipments to Miami")
        # Agent asks: "Which Miami: Port of Miami or Miami Container Terminal?"

        # User answers
        response = agent.run_turn("Port of Miami")
        # Agent returns: "Found 42 shipments to Port of Miami"

        # User modifies
        response = agent.run_turn("Also include arrival date")
        # Agent replans and executes

        # Clear conversation
        agent.clear_memory()
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize agent with all dependencies.

        Args:
            settings: Application settings (loads from .env if None)

        Implementation Flow:
            1. Load settings
            2. Setup services (LLM, embedding, vector DB)
            3. Setup memory (short-term, long-term, manager)
            4. Setup tools and registry
            5. Create and compile graph
            6. Initialize turn counter

        Implementation Notes:
            - Services created once, reused across turns
            - Tools registered once at init
            - Graph compiled once
            - Memory persists across turns
            - Turn counter tracks total TODOs executed
        """
        # TODO: Load settings
        # self.settings = settings or Settings()

        # TODO: Setup services
        # self.llm_service = LLMService(self.settings)
        # self.embedding_service = EmbeddingService(self.settings)
        # self.vectordb_service = create_vectordb_service(
        #     self.settings,
        #     embedding_service=self.embedding_service
        # )

        # TODO: Setup memory
        # self.short_term_memory = ShortTermMemory(
        #     max_turns=self.settings.short_term_memory_turns
        # )
        # self.long_term_memory = LongTermMemory(
        #     vectordb_service=self.vectordb_service,
        #     embedding_service=self.embedding_service,
        #     collection_name="conversation_history"
        # )
        # self.memory_manager = MemoryManager(self.short_term_memory)

        # TODO: Setup tools
        # self.tool_registry = ToolRegistry(mode="local")
        # self._register_tools()

        # TODO: Setup graph
        # checkpointer = create_checkpointer(self.settings)
        # self.graph = create_bi_graph(
        #     tool_registry=self.tool_registry,
        #     settings=self.settings,
        #     checkpointer=checkpointer
        # )

        # TODO: Initialize turn counter
        # self.turn_counter = 0

        raise NotImplementedError("Initialize BIAgent")

    def _register_tools(self):
        """
        Register all tools with registry.

        Tools Registered:
            - llm_tool: LLM completion
            - embedding_tool: Text embeddings
            - vectordb_tool: Vector search
            - field_mapping_tool: Business term → schema mapping
            - es_executor: Elasticsearch query execution
            - graphql_executor: GraphQL query execution
            - es_query_builder: Elasticsearch query construction
            - graphql_query_builder: GraphQL query construction

        Implementation Notes:
            - Each tool initialized with required services
            - Tools are stateless (no state access)
            - LLM-enabled tools have can_clarify=True
            - Traditional tools have can_clarify=False
        """
        # TODO: Register LLM tool
        # llm_tool = LLMTool(self.llm_service)
        # self.tool_registry.register(llm_tool)

        # TODO: Register embedding tool
        # embedding_tool = EmbeddingTool(self.embedding_service)
        # self.tool_registry.register(embedding_tool)

        # TODO: Register vector DB tool
        # vectordb_tool = VectorDBTool(
        #     vectordb_service=self.vectordb_service,
        #     embedding_tool=embedding_tool
        # )
        # self.tool_registry.register(vectordb_tool)

        # TODO: Register field mapping tool
        # field_mapping_tool = FieldMappingTool(self.vectordb_service)
        # self.tool_registry.register(field_mapping_tool)

        # TODO: Register data source executors
        # es_executor = ESExecutorTool(self.settings)
        # self.tool_registry.register(es_executor)
        # graphql_executor = GraphQLExecutorTool(self.settings)
        # self.tool_registry.register(graphql_executor)

        # TODO: Register query builders
        # es_builder = ESQueryBuilderTool()
        # self.tool_registry.register(es_builder)
        # graphql_builder = GraphQLQueryBuilderTool()
        # self.tool_registry.register(graphql_builder)

        raise NotImplementedError("Register tools")

    def run_turn(self, user_input: str, thread_id: str = "default") -> str:
        """
        Execute one complete user request turn.

        IMPORTANT: This may execute multiple TODOs and save multiple memory entries.
        The turn ends when:
            - Clarification needed (ask user)
            - Error occurs (report error)
            - All TODOs complete (return results)

        Args:
            user_input: User's message (original request or clarification answer)
            thread_id: Conversation thread identifier (for checkpointing)

        Returns:
            Agent's response (clarification question, results, or error)

        Implementation Flow:
            1. Increment turn counter (for this user input, not per TODO)
            2. Initialize state via memory_manager.start_turn()
            3. Inject short-term memory context
            4. Run graph (cyclic execution happens here)
               - classify_intent checks TODO list validity
               - Routes to reiterate → plan_todos OR execute_next_todo
               - execute_next_todo loops until clarification/error/completion
            5. Extract final state
            6. Save memory for each TODO executed
               - CRITICAL: If 5 TODOs executed, save 5 ConversationTurns
               - Each TODO completion = 1 memory entry
            7. Persist to long-term memory (async)
            8. Return agent_response

        Memory Saving Strategy:
            OLD: 1 memory entry at end of turn
            NEW: 1 memory entry per TODO completion

            Implementation:
                - After graph execution, check which TODOs completed
                - For each completed TODO in active_todo_list:
                    - Call memory_manager.save_todo_completion()
                    - Persist to long_term_memory
                - This creates detailed history (5 TODOs = 5 memory entries)

        Example Scenarios:

        Scenario 1: Simple Request (No Clarification)
            Input: "Show shipments to Miami"
            Graph execution:
                1. classify_intent → new_request
                2. reiterate_intention → "Show all shipments to Miami"
                3. plan_todos → 5 TODOs
                4. execute_next_todo → resolve_entities (success)
                5. execute_next_todo → map_fields (success)
                6. execute_next_todo → build_query (success)
                7. execute_next_todo → execute_query (success)
                8. execute_next_todo → format_results (success)
                9. format_response → END
            Memory saved: 5 ConversationTurns (1 per TODO)
            Response: "Found 42 shipments to Miami"

        Scenario 2: Clarification Needed
            Input: "Show shipments to Miami"
            Graph execution:
                1. classify_intent → new_request
                2. reiterate_intention
                3. plan_todos
                4. execute_next_todo → resolve_entities (clarification)
                   Tool asks: "Which Miami?"
                   Turn ENDS
            Memory saved: 1 ConversationTurn (clarification)
            Response: "Which Miami: Port of Miami or Miami Container Terminal?"

        Scenario 3: User Answers Exact Question
            Input: "Port of Miami"
            Graph execution:
                1. classify_intent → exact_answer
                2. execute_next_todo → resolve_entities (rerun with answer, success)
                3. execute_next_todo → map_fields (success)
                4. execute_next_todo → build_query (success)
                5. execute_next_todo → execute_query (success)
                6. execute_next_todo → format_results (success)
                7. format_response → END
            Memory saved: 5 ConversationTurns (4 new + clarification already saved)
            Response: "Found 42 shipments to Port of Miami"

        Scenario 4: User Modifies Request
            Input: "Port of Miami, but also arrival date"
            Graph execution:
                1. classify_intent → modification (ditches old TODO list)
                2. reiterate_intention → "Show shipments to Port of Miami with arrival date"
                3. plan_todos → new 5 TODOs
                4-8. execute_next_todo (loop)
                9. format_response → END
            Memory saved: 5 ConversationTurns (new execution)
            Response: "Found 42 shipments with arrival dates"

        Error Handling:
            - If graph execution fails, return error message
            - If TODO execution fails, error captured in state
            - Memory still saved for failed TODOs (for debugging)
            - Return user-friendly error message

        Performance:
            - Each TODO may take 1-5 seconds
            - LLM calls slower than traditional tools
            - Consider timeout for long-running queries
            - Turn may take 10-30 seconds total

        Raises:
            Should NOT raise - return error message in response
        """
        # TODO: Increment turn counter
        # self.turn_counter += 1

        # TODO: Initialize state
        # initial_state = self.memory_manager.start_turn(
        #     turn_id=self.turn_counter,
        #     user_input=user_input
        # )

        # TODO: Inject memory context
        # context = self.memory_manager.get_context_for_prompt(n_turns=3)
        # if context:
        #     initial_state["messages"] = [{
        #         "role": "system",
        #         "content": f"Recent conversation:\n{context}"
        #     }]

        # TODO: Run graph (cyclic execution)
        # config = {"configurable": {"thread_id": thread_id}}
        # try:
        #     final_state = self.graph.invoke(initial_state, config)
        # except Exception as e:
        #     return f"Error during execution: {str(e)}"

        # TODO: Extract completed TODOs from state
        # active_todo_list = final_state.get("active_todo_list", {})
        # completed_tasks = active_todo_list.get("completed_tasks", [])
        # tasks = active_todo_list.get("tasks", {})

        # TODO: Save memory for each completed TODO
        # for task_key in completed_tasks:
        #     task = tasks[task_key]
        #     task_result = task.get("result", {})
        #     agent_response = build_todo_response(task_key, task_result)
        #
        #     # Save to short-term memory
        #     turn = self.memory_manager.save_todo_completion(
        #         state=final_state,
        #         task_key=task_key,
        #         task_result=task_result,
        #         agent_response_text=agent_response
        #     )
        #
        #     # Persist to long-term memory (async)
        #     try:
        #         self.long_term_memory.persist_turn(turn)
        #     except Exception as e:
        #         print(f"Warning: Failed to persist turn {turn.turn_id}: {e}")

        # TODO: Return final response
        # return final_state.get("agent_response", "I encountered an error processing your request.")

        raise NotImplementedError("Run turn")

    def get_conversation_history(self) -> list[ConversationTurn]:
        """
        Get full conversation history.

        Returns:
            List of all ConversationTurns in short-term memory

        Implementation Notes:
            - Returns TODO-level history (each TODO = 1 turn)
            - Only includes recent turns (limited by max_turns)
            - For full history, query long_term_memory
        """
        return self.short_term_memory.turns

    def get_active_todo_list(self) -> dict | None:
        """
        Get current active TODO list.

        Returns:
            TodoListContext dict or None if no active list

        Implementation Notes:
            - Check checkpointed state for active_todo_list
            - Used for debugging or UI display
            - Shows which TODOs completed, which pending
        """
        # TODO: Retrieve from checkpointed state
        # May need to access LangGraph checkpoint
        raise NotImplementedError("Get active TODO list")

    def clear_memory(self):
        """
        Clear conversation memory (start fresh).

        Clears:
            - Short-term memory (recent TODOs)
            - Turn counter reset
            - Active TODO list (via checkpoint clear)

        Does NOT clear:
            - Long-term memory (vector DB) - permanent storage
            - Tool registry (reused)
            - Graph (reused)

        Implementation Notes:
            - Called when user explicitly clears conversation
            - Useful for testing or fresh start
            - Checkpoint may need separate clearing
        """
        self.short_term_memory.clear()
        self.turn_counter = 0
        # TODO: Clear checkpointed state if needed


def build_todo_response(task_key: str, task_result: dict) -> str:
    """
    Build user-facing response for TODO completion.

    Args:
        task_key: Completed task key
        task_result: ToolResult from execution

    Returns:
        Human-readable response string

    Example:
        task_key="resolve_entities", success=True
        → "Resolved entities: MSC ANNA (vessel), Port of Miami (port)"

        task_key="execute_query", success=True, record_count=42
        → "Query executed successfully: 42 records found"

    Implementation Notes:
        - Format based on task_key and result type
        - Keep concise for memory efficiency
        - Used in memory entries
    """
    # TODO: Format response based on task_key
    # Check task_result.success
    # Extract relevant data
    # Build user-friendly message
    raise NotImplementedError("Build TODO response")


def main():
    """
    Example usage - interactive CLI.

    Demonstrates cyclic TODO-based execution with clarification handling.
    """
    # TODO: Initialize agent
    # settings = Settings()
    # agent = BIAgent(settings)

    # print("BI Agent initialized (TODO-based execution).")
    # print("Type 'quit' to exit, 'clear' to clear memory.")

    # while True:
    #     user_input = input("\nYou: ").strip()

    #     if user_input.lower() in ['quit', 'exit']:
    #         break

    #     if user_input.lower() == 'clear':
    #         agent.clear_memory()
    #         print("Memory cleared.")
    #         continue

    #     if not user_input:
    #         continue

    #     # Run turn (may execute multiple TODOs)
    #     response = agent.run_turn(user_input)
    #     print(f"\nAgent: {response}")

    #     # Optional: Show TODO progress
    #     todo_list = agent.get_active_todo_list()
    #     if todo_list:
    #         completed = len(todo_list.get("completed_tasks", []))
    #         total = todo_list.get("total_tasks", 0)
    #         if completed < total:
    #             print(f"(Progress: {completed}/{total} tasks completed)")

    raise NotImplementedError("Main CLI loop")


if __name__ == "__main__":
    main()
