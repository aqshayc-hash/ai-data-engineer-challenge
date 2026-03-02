"""Dagster assets for Reddit data ingestion."""

import json
from datetime import datetime

from dagster import asset, get_dagster_logger

from mama_health.config import AppConfig
from mama_health.reddit_client import RedditClient

logger = get_dagster_logger()


@asset
def reddit_client() -> RedditClient:
    """Initialize Reddit API client.

    Returns:
        Configured RedditClient instance
    """
    config = AppConfig()
    return RedditClient(config.reddit)


@asset
def raw_posts(reddit_client: RedditClient) -> list[dict]:
    """Fetch raw posts from subreddit.

    This asset retrieves posts from the configured subreddit using the Reddit API.
    Posts are stored as dictionaries (JSON-serializable format).

    Args:
        reddit_client: Configured Reddit API client

    Returns:
        List of dictionaries representing Reddit posts
    """
    config = AppConfig()

    logger.info(
        f"Fetching posts from r/{config.pipeline.target_subreddit} "
        f"(limit: {config.pipeline.posts_limit})"
    )

    posts = reddit_client.fetch_posts(
        subreddit_name=config.pipeline.target_subreddit,
        limit=config.pipeline.posts_limit,
        time_filter="month",
    )

    # Convert to dictionaries for storage
    posts_dict = [
        {
            "post_id": post.id,
            "title": post.title,
            "content": post.selftext,
            "author": post.author.name if post.author else "[deleted]",
            "subreddit": post.subreddit.display_name,
            "score": post.score,
            "num_comments": post.num_comments,
            "created_at": datetime.fromtimestamp(post.created_utc).isoformat(),
            "url": post.url,
        }
        for post in posts
    ]

    logger.info(f"Successfully fetched {len(posts_dict)} posts")
    return posts_dict


@asset
def posts_with_comments(reddit_client: RedditClient) -> list[dict]:
    """Fetch posts with their comments from subreddit.

    This asset retrieves complete posts including all comments, implementing
    the full workflow for gathering community discussion around health topics.

    Args:
        reddit_client: Configured Reddit API client

    Returns:
        List of dictionaries representing posts with nested comments
    """
    config = AppConfig()

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
        for post in posts
    ]

    logger.info(
        f"Successfully fetched {len(posts_dict)} posts with "
        f"{sum(len(p['comments']) for p in posts_dict)} total comments"
    )
    return posts_dict


@asset
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


@asset
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

    created_dates = [
        datetime.fromisoformat(post["created_at"])
        for post in posts_with_comments
    ]
    date_range = {
        "earliest": min(created_dates).isoformat() if created_dates else None,
        "latest": max(created_dates).isoformat() if created_dates else None,
    }

    metadata = {
        "ingestion_timestamp": datetime.utcnow().isoformat(),
        "subreddit": config.pipeline.target_subreddit,
        "total_posts": len(posts_with_comments),
        "total_comments": total_comments,
        "avg_comments_per_post": total_comments / len(posts_with_comments) if posts_with_comments else 0,
        "total_score": total_score,
        "avg_post_score": avg_score,
        "date_range": date_range,
    }

    logger.info(f"Ingestion metadata: {metadata}")
    return metadata
