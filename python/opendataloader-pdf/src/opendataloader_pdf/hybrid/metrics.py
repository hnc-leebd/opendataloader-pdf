"""Performance metrics tracking for hybrid pipeline."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PhaseMetrics:
    """Metrics for a single pipeline phase."""

    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    items_processed: int = 0

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        if self.end_time == 0.0:
            return 0.0
        return self.end_time - self.start_time

    @property
    def items_per_second(self) -> float:
        """Processing rate."""
        if self.duration == 0.0 or self.items_processed == 0:
            return 0.0
        return self.items_processed / self.duration

    def start(self) -> None:
        """Mark phase start."""
        self.start_time = time.perf_counter()

    def stop(self, items: int = 0) -> None:
        """Mark phase end."""
        self.end_time = time.perf_counter()
        self.items_processed = items


@dataclass
class PipelineMetrics:
    """Aggregated metrics for the entire pipeline."""

    jar_phase: PhaseMetrics = field(default_factory=lambda: PhaseMetrics("jar"))
    ai_phase: PhaseMetrics = field(default_factory=lambda: PhaseMetrics("ai"))
    merge_phase: PhaseMetrics = field(default_factory=lambda: PhaseMetrics("merge"))

    total_pages: int = 0
    fast_pages: int = 0
    ai_pages: int = 0
    ai_page_range: list[int] = field(default_factory=list)

    _pipeline_start: float = field(default=0.0, repr=False)
    _pipeline_end: float = field(default=0.0, repr=False)

    def start_pipeline(self) -> None:
        """Mark pipeline start."""
        self._pipeline_start = time.perf_counter()

    def stop_pipeline(self) -> None:
        """Mark pipeline end."""
        self._pipeline_end = time.perf_counter()

    @property
    def total_duration(self) -> float:
        """Total pipeline duration."""
        if self._pipeline_end == 0.0:
            return 0.0
        return self._pipeline_end - self._pipeline_start

    @property
    def ai_ratio(self) -> float:
        """Ratio of AI pages to total pages."""
        if self.total_pages == 0:
            return 0.0
        return self.ai_pages / self.total_pages

    @property
    def theoretical_speedup(self) -> float:
        """Theoretical speedup if AI processing were instant.

        Returns the speedup we'd get over pure docling
        if we only had to process fast pages.
        """
        if self.total_pages == 0:
            return 1.0
        return self.total_pages / max(self.ai_pages, 1)

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "",
            "=" * 70,
            f"Pipeline Metrics ({self.total_pages} pages)",
            "=" * 70,
            f"Page routing: {self.fast_pages} fast, {self.ai_pages} AI ({self.ai_ratio:.0%})",
            f"AI pages: {self.ai_page_range}" if self.ai_page_range else "AI pages: none",
            "=" * 70,
            f"{'Phase':<20} {'Duration':>10} {'Items':>8} {'Rate':>12}",
            "-" * 70,
        ]

        for phase in [self.jar_phase, self.ai_phase, self.merge_phase]:
            rate = f"{phase.items_per_second:.1f}/s" if phase.items_per_second > 0 else "-"
            items = str(phase.items_processed) if phase.items_processed > 0 else "-"
            lines.append(f"{phase.name:<20} {phase.duration:>9.2f}s {items:>8} {rate:>12}")

        lines.extend([
            "-" * 70,
            f"{'Total':<20} {self.total_duration:>9.2f}s",
            "=" * 70,
        ])

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_duration": self.total_duration,
            "total_pages": self.total_pages,
            "fast_pages": self.fast_pages,
            "ai_pages": self.ai_pages,
            "ai_ratio": self.ai_ratio,
            "ai_page_range": self.ai_page_range,
            "phases": {
                "jar": {
                    "duration": self.jar_phase.duration,
                    "items": self.jar_phase.items_processed,
                },
                "ai": {
                    "duration": self.ai_phase.duration,
                    "items": self.ai_phase.items_processed,
                    "seconds_per_page": (
                        self.ai_phase.duration / self.ai_phase.items_processed
                        if self.ai_phase.items_processed > 0
                        else 0
                    ),
                },
                "merge": {
                    "duration": self.merge_phase.duration,
                    "items": self.merge_phase.items_processed,
                },
            },
        }


class MetricsContext:
    """Context manager for timing a phase."""

    def __init__(self, phase: PhaseMetrics, items: Optional[int] = None):
        self.phase = phase
        self.items = items

    def __enter__(self) -> "MetricsContext":
        self.phase.start()
        return self

    def __exit__(self, *args) -> None:
        self.phase.stop(self.items or 0)

    def set_items(self, items: int) -> None:
        """Set items count (can be called during the phase)."""
        self.items = items
