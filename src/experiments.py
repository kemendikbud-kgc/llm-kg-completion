"""Experiment tracking for comparing extraction configurations."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

EXPERIMENTS_DIR = Path("data/experiments")


@dataclass
class ExperimentRun:
    """Represents a single experiment run with its configuration and metrics."""

    id: str  # Unique run ID
    timestamp: str  # ISO timestamp
    document_name: str  # Source document
    model: str  # LLM model used
    prompt_name: str  # Prompt from registry
    embedding_model: str  # Embedding model used
    similarity_threshold: float
    # Extraction metrics
    topic_count: int
    subtopic_count: int
    # Graph quality metrics (after completion)
    adc: float = 0.0
    modularity: float = 0.0
    density: float = 0.0
    similar_pairs_count: int = 0
    # Content filtering stats
    filter_enabled: bool = False
    filter_reduction_percent: float = 0.0
    # Optional notes
    notes: str = ""
    # Additional metadata
    metadata: dict = field(default_factory=dict)


def generate_experiment_id() -> str:
    """Generate a unique experiment ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"exp_{timestamp}_{short_uuid}"


def save_experiment(run: ExperimentRun) -> Path:
    """Save an experiment run to disk.

    Args:
        run: ExperimentRun to save

    Returns:
        Path to the saved file
    """
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPERIMENTS_DIR / f"{run.id}.json"
    path.write_text(json.dumps(asdict(run), indent=2, ensure_ascii=False))
    return path


def load_experiment(experiment_id: str) -> ExperimentRun | None:
    """Load a single experiment by ID.

    Args:
        experiment_id: The experiment ID to load

    Returns:
        ExperimentRun or None if not found
    """
    path = EXPERIMENTS_DIR / f"{experiment_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExperimentRun(**data)


def load_experiments() -> list[ExperimentRun]:
    """Load all experiments from disk.

    Returns:
        List of ExperimentRun sorted by timestamp (newest first)
    """
    if not EXPERIMENTS_DIR.exists():
        return []
    runs = []
    for f in EXPERIMENTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            runs.append(ExperimentRun(**data))
        except (json.JSONDecodeError, TypeError):
            # Skip malformed experiment files
            continue
    return sorted(runs, key=lambda r: r.timestamp, reverse=True)


def delete_experiment(experiment_id: str) -> bool:
    """Delete an experiment by ID.

    Args:
        experiment_id: The experiment ID to delete

    Returns:
        True if deleted, False if not found
    """
    path = EXPERIMENTS_DIR / f"{experiment_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def compare_experiments(run1: ExperimentRun, run2: ExperimentRun) -> dict:
    """Compare two experiment runs.

    Args:
        run1: First experiment
        run2: Second experiment

    Returns:
        Dict with differences between the runs
    """
    return {
        "topic_diff": run1.topic_count - run2.topic_count,
        "subtopic_diff": run1.subtopic_count - run2.subtopic_count,
        "adc_diff": run1.adc - run2.adc,
        "modularity_diff": run1.modularity - run2.modularity,
        "density_diff": run1.density - run2.density,
        "pairs_diff": run1.similar_pairs_count - run2.similar_pairs_count,
        "config_changes": {
            "model": (run1.model, run2.model) if run1.model != run2.model else None,
            "prompt": (run1.prompt_name, run2.prompt_name)
            if run1.prompt_name != run2.prompt_name
            else None,
            "embedding_model": (run1.embedding_model, run2.embedding_model)
            if run1.embedding_model != run2.embedding_model
            else None,
            "threshold": (run1.similarity_threshold, run2.similarity_threshold)
            if run1.similarity_threshold != run2.similarity_threshold
            else None,
        },
    }


def get_experiment_summary(run: ExperimentRun) -> dict:
    """Get a summary of an experiment for display.

    Args:
        run: ExperimentRun to summarize

    Returns:
        Dict with display-friendly summary
    """
    return {
        "id": run.id,
        "timestamp": run.timestamp,
        "document": run.document_name,
        "model": run.model.split("/")[-1] if "/" in run.model else run.model,
        "prompt": run.prompt_name,
        "topics": run.topic_count,
        "subtopics": run.subtopic_count,
        "similar_pairs": run.similar_pairs_count,
        "adc": f"{run.adc:.3f}",
        "modularity": f"{run.modularity:.3f}",
    }
