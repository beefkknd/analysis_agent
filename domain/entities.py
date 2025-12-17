"""Entity domain objects.

Entities represent business concepts mentioned in user queries:
- Vessels, ports, terminals, countries, etc.
- Extracted from user input, resolved to canonical forms
"""

from pydantic import BaseModel, Field
from typing import Any, Literal


class Entity(BaseModel):
    """
    Base entity class for extracted mentions.

    Represents an entity mention from user input before resolution.

    Fields:
        name: Raw entity mention from user
            Example: "Anna", "Miami", "Shanghai"

        entity_type: Type of entity
            Example: "vessel", "port", "terminal", "country"

        metadata: Additional context about extraction
            Example: {
                "source": "user_input",
                "position": 5,
                "confidence": 0.92,
                "context": "Show shipments from Anna to Miami"
            }

    Example:
        Entity(
            name="Anna",
            entity_type="vessel",
            metadata={"source": "user_input", "confidence": 0.85}
        )

    Implementation Notes:
        - Used for initial extraction before resolution
        - May be ambiguous (multiple matches possible)
        - Passed to entity_resolution tool for clarification
    """
    name: str
    entity_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()


class ResolvedEntity(BaseModel):
    """
    Entity after resolution to canonical form.

    Represents a successfully resolved entity with unique identifier.

    Fields:
        original_value: Raw mention from user input
            Example: "Anna", "Miami"

        resolved_name: Canonical name after resolution
            Example: "MSC ANNA", "Port of Miami"

        entity_type: Type of entity
            Example: "vessel", "port", "terminal"

        entity_id: Unique identifier (IMO, LOCODE, etc.)
            Example: "IMO9876543", "USMIAMI1"
            Can be None if no ID available

        confidence: Resolution confidence score (0.0-1.0)
            Example: 0.95 (high confidence), 0.60 (low confidence)

        source: Where resolution came from
            Example: "vector_db", "elasticsearch", "exact_match"

        metadata: Additional context
            Example: {
                "search_method": "semantic",
                "alternatives": [...],
                "matched_field": "vessel_name"
            }

    Example:
        ResolvedEntity(
            original_value="Anna",
            resolved_name="MSC ANNA",
            entity_type="vessel",
            entity_id="IMO9876543",
            confidence=0.95,
            source="vector_db",
            metadata={"search_method": "semantic"}
        )

    Implementation Notes:
        - Created by entity_resolution tool
        - Used in query building to substitute canonical names/IDs
        - Confidence < 0.7 may trigger clarification
    """
    original_value: str
    resolved_name: str
    entity_type: str
    entity_id: str | None = None
    confidence: float
    source: Literal["vector_db", "elasticsearch", "graphql", "exact_match", "fuzzy_match"] = "vector_db"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """
        Check if resolution is high confidence.

        Args:
            threshold: Confidence threshold (default: 0.8)

        Returns:
            True if confidence >= threshold

        Implementation Notes:
            - Used to decide if clarification needed
            - Typical threshold: 0.7-0.9
        """
        return self.confidence >= threshold


class AmbiguousEntity(BaseModel):
    """
    Entity with multiple possible matches requiring clarification.

    When entity_resolution finds multiple high-confidence matches,
    it returns an AmbiguousEntity for user clarification.

    Fields:
        original_value: Raw mention from user input
            Example: "Miami"

        entity_type: Type of entity
            Example: "port"

        candidates: List of possible matches
            Each candidate is a ResolvedEntity
            Example: [
                ResolvedEntity(resolved_name="Port of Miami", ...),
                ResolvedEntity(resolved_name="Miami Container Terminal", ...)
            ]

        clarification_message: Question to ask user
            Example: "Which Miami do you mean: Port of Miami or Miami Container Terminal?"

        metadata: Additional context
            Example: {"search_method": "semantic", "all_similar_score": True}

    Example:
        AmbiguousEntity(
            original_value="Miami",
            entity_type="port",
            candidates=[
                ResolvedEntity(resolved_name="Port of Miami", confidence=0.88, ...),
                ResolvedEntity(resolved_name="Miami Container Terminal", confidence=0.86, ...)
            ],
            clarification_message="Which Miami: Port of Miami or Miami Container Terminal?"
        )

    Implementation Notes:
        - Created by entity_resolution tool when ambiguous
        - Triggers clarification turn (agent asks user)
        - User's answer used to rerun entity_resolution
    """
    original_value: str
    entity_type: str
    candidates: list[ResolvedEntity]
    clarification_message: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def format_options(self) -> str:
        """
        Format candidates as numbered list for user.

        Returns:
            Formatted string with options
            Example:
                1. Port of Miami (USMIAMI1)
                2. Miami Container Terminal (USMIAMI2)

        Implementation Notes:
            - Used in clarification prompts
            - Shows canonical name + ID for clarity
        """
        lines = []
        for i, candidate in enumerate(self.candidates, 1):
            id_str = f" ({candidate.entity_id})" if candidate.entity_id else ""
            lines.append(f"{i}. {candidate.resolved_name}{id_str}")
        return "\n".join(lines)


class EntityResolutionResult(BaseModel):
    """
    Complete result from entity resolution process.

    Returned by entity_resolution tool with all resolution outcomes.

    Fields:
        resolved: Successfully resolved entities (high confidence, no ambiguity)
            Dict mapping entity_type to list of ResolvedEntity
            Example: {"vessel": [ResolvedEntity(...), ...]}

        ambiguous: Entities requiring clarification (multiple matches)
            Dict mapping entity_type to list of AmbiguousEntity
            Example: {"port": [AmbiguousEntity(...), ...]}

        unresolved: Entities that couldn't be resolved at all
            Dict mapping entity_type to list of original values
            Example: {"country": ["Atlantis"]}  # Not found

        needs_clarification: Whether any ambiguous entities exist
            True if len(ambiguous) > 0

        clarification_questions: List of questions to ask user
            Example: [
                "Which Miami: Port of Miami or Miami Container Terminal?",
                "Which Anna: MSC ANNA or CMA CGM ANNA?"
            ]

    Example:
        EntityResolutionResult(
            resolved={"vessel": [ResolvedEntity(resolved_name="MSC ANNA", ...)]},
            ambiguous={"port": [AmbiguousEntity(original_value="Miami", ...)]},
            unresolved={},
            needs_clarification=True,
            clarification_questions=["Which Miami: Port of Miami or Miami Container Terminal?"]
        )

    Implementation Notes:
        - Returned by entity_resolution tool
        - If needs_clarification=True, turn ends with agent asking questions
        - If needs_clarification=False, TODO marked complete, move to next
    """
    resolved: dict[str, list[ResolvedEntity]] = Field(default_factory=dict)
    ambiguous: dict[str, list[AmbiguousEntity]] = Field(default_factory=dict)
    unresolved: dict[str, list[str]] = Field(default_factory=dict)
    needs_clarification: bool = False
    clarification_questions: list[str] = Field(default_factory=list)

    def has_any_resolved(self) -> bool:
        """Check if any entities were resolved."""
        return len(self.resolved) > 0

    def get_all_resolved_entities(self) -> list[ResolvedEntity]:
        """
        Get flat list of all resolved entities.

        Returns:
            List of all resolved entities across all types

        Implementation Notes:
            - Useful for query building
            - Flattens nested dict structure
        """
        entities = []
        for entity_list in self.resolved.values():
            entities.extend(entity_list)
        return entities

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()
