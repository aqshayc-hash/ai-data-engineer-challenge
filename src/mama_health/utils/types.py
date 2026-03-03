"""Type aliases used across the mama health pipeline.

Centralising type aliases here avoids repeating verbose generics (e.g.
``list[dict[str, Any]]``) in every module and makes the intent of function
signatures self-documenting.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Raw Reddit data (as produced by the ingestion assets)
# ---------------------------------------------------------------------------

CommentDict = dict[str, Any]
"""A single Reddit comment serialised to a plain dict.

Expected keys (from RedditComment.model_dump()):
    comment_id, post_id, author, text, score, created_at, parent_comment_id
"""

PostDict = dict[str, Any]
"""A single Reddit post serialised to a plain dict, including nested comments.

Expected keys (from RedditPost.model_dump()):
    post_id, title, content, author, subreddit, score, num_comments,
    created_at, url, comments: list[CommentDict]
"""

PostList = list[PostDict]
"""A collection of serialised Reddit posts returned by posts_with_comments."""

# ---------------------------------------------------------------------------
# LLM extraction outputs
# ---------------------------------------------------------------------------

# PatientJourneyEvent is a Pydantic model; EventList is used in asset
# signatures where the full import would create a circular dependency.
EventList = list[Any]  # list[PatientJourneyEvent]
"""A list of PatientJourneyEvent instances (typed as Any to avoid circular imports)."""

SymptomRecord = dict[str, Any]
"""A single symptom extracted by the specialised symptom prompt variant.

Expected keys: name, onset, duration, severity, triggers, source_post_id,
source_created_at
"""

MedicationRecord = dict[str, Any]
"""A single medication extracted by the specialised medication prompt variant.

Expected keys: name, dosage, indication, efficacy, side_effects,
source_post_id, source_created_at
"""

# ---------------------------------------------------------------------------
# General-purpose
# ---------------------------------------------------------------------------

JsonDict = dict[str, Any]
"""An arbitrary JSON-serialisable dict — used for analytics output assets."""
