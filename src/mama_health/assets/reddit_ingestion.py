"""Dagster assets for Reddit data ingestion."""

import json
import os
from datetime import datetime, timedelta

from dagster import AssetExecutionContext, asset, get_dagster_logger

from mama_health.config import AppConfig
from mama_health.partitions import daily_partitions
from mama_health.reddit_client import RedditClient

logger = get_dagster_logger()

CHECKPOINT_FILE = os.environ.get("CHECKPOINT_PATH", ".ingestion_checkpoint.json")


def _load_checkpoint() -> datetime | None:
    """Load the last ingestion checkpoint timestamp.

    Returns:
        Datetime of last successful ingestion, or None if no checkpoint exists
    """
    if not os.path.exists(CHECKPOINT_FILE):
        return None
    try:
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
        return datetime.fromisoformat(data["last_ingested_at"])
    except Exception as e:
        logger.warning(f"Failed to load checkpoint: {e}")
        return None


def _save_checkpoint(timestamp: datetime) -> None:
    """Save the ingestion checkpoint timestamp.

    Args:
        timestamp: Datetime to save as last successful ingestion
    """
    try:
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump({"last_ingested_at": timestamp.isoformat()}, f)
        logger.info(f"Checkpoint saved: {timestamp.isoformat()}")
    except Exception as e:
        logger.warning(f"Failed to save checkpoint: {e}")


@asset(group_name="ingestion")
def reddit_client() -> RedditClient:
    """Initialize Reddit API client.

    Returns:
        Configured RedditClient instance
    """
    config = AppConfig()
    return RedditClient(config.reddit)


@asset(group_name="ingestion", partitions_def=daily_partitions)
def posts_with_comments(
    context: AssetExecutionContext,
    reddit_client: RedditClient,
) -> list[dict]:
    """Fetch posts with their comments from subreddit for a specific day partition.

    This asset retrieves complete posts including all comments for the calendar
    day identified by the partition key. Each day is an independent, replayable
    unit — enabling historical backfills and preventing re-processing of
    already-ingested days.

    Args:
        context: Dagster asset execution context (provides partition_key)
        reddit_client: Configured Reddit API client

    Returns:
        List of dictionaries representing posts with nested comments
    """
    config = AppConfig()

    # Determine the partition window (naive UTC datetimes to match post.created_at)
    start_dt = datetime.strptime(context.partition_key, "%Y-%m-%d")
    end_dt = start_dt + timedelta(days=1)
    logger.info(
        f"Fetching posts for partition {context.partition_key} "
        f"(window: {start_dt.isoformat()} — {end_dt.isoformat()})"
    )

    logger.info(
        f"Fetching posts with comments from r/{config.pipeline.target_subreddit} "
        f"(posts: {config.pipeline.posts_limit}, comments: {config.pipeline.comments_limit})"
    )

    posts = reddit_client.fetch_posts_with_comments(
        subreddit_name=config.pipeline.target_subreddit,
        posts_limit=config.pipeline.posts_limit,
        comments_limit=config.pipeline.comments_limit,
        time_filter="month",
    )

    # Apply date filter — keep only posts within the partition window
    filtered_posts = [p for p in posts if start_dt <= p.created_at < end_dt]

    logger.info(
        f"Date filter: {len(posts)} fetched → {len(filtered_posts)} posts in partition window"
    )

    # Convert to dictionaries for storage
    posts_dict = [
        {
            "post_id": post.post_id,
            "title": post.title,
            "content": post.content,
            "author": post.author,
            "subreddit": post.subreddit,
            "score": post.score,
            "num_comments": post.num_comments,
            "created_at": post.created_at.isoformat(),
            "url": post.url,
            "comments": [
                {
                    "comment_id": comment.comment_id,
                    "post_id": comment.post_id,
                    "author": comment.author,
                    "text": comment.text,
                    "score": comment.score,
                    "created_at": comment.created_at.isoformat(),
                    "parent_comment_id": comment.parent_comment_id,
                }
                for comment in post.comments
            ],
        }
        for post in filtered_posts
    ]

    logger.info(
        f"Successfully fetched {len(posts_dict)} posts with "
        f"{sum(len(p['comments']) for p in posts_dict)} total comments"  # type: ignore[misc, arg-type]
    )
    return posts_dict


@asset(group_name="ingestion", partitions_def=daily_partitions)
def raw_posts_json(posts_with_comments: list[dict]) -> str:
    """Store raw posts as JSON blob.

    This asset saves the complete raw data for archival and audit purposes.

    Args:
        posts_with_comments: List of posts with comments

    Returns:
        JSON string containing all raw data
    """
    json_data = json.dumps(posts_with_comments, indent=2, default=str)
    logger.info(f"Stored raw posts JSON ({len(json_data)} bytes)")
    return json_data


@asset(group_name="ingestion", partitions_def=daily_partitions)
def posts_metadata(posts_with_comments: list[dict]) -> dict:
    """Extract metadata about the ingestion.

    This asset computes summary statistics about the fetched data.

    Args:
        posts_with_comments: List of posts with comments

    Returns:
        Dictionary containing ingestion metadata
    """
    config = AppConfig()

    total_comments = sum(len(post.get("comments", [])) for post in posts_with_comments)
    total_score = sum(post.get("score", 0) for post in posts_with_comments)
    avg_score = total_score / len(posts_with_comments) if posts_with_comments else 0

    created_dates = [datetime.fromisoformat(post["created_at"]) for post in posts_with_comments]
    date_range = {
        "earliest": min(created_dates).isoformat() if created_dates else None,
        "latest": max(created_dates).isoformat() if created_dates else None,
    }

    metadata = {
        "ingestion_timestamp": datetime.utcnow().isoformat(),
        "subreddit": config.pipeline.target_subreddit,
        "total_posts": len(posts_with_comments),
        "total_comments": total_comments,
        "avg_comments_per_post": total_comments / len(posts_with_comments)
        if posts_with_comments
        else 0,
        "total_score": total_score,
        "avg_post_score": avg_score,
        "date_range": date_range,
    }

    logger.info(f"Ingestion metadata: {metadata}")
    return metadata
