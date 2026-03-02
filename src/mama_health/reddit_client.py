"""Reddit API client wrapper with rate limiting and error handling."""

import logging
import time
from datetime import datetime
from typing import Optional

import praw
from praw.exceptions import PRAWException as PrawException
from praw.models import Submission

from mama_health.config import RedditConfig
from mama_health.models import RedditComment, RedditPost

logger = logging.getLogger(__name__)


class RedditClient:
    """Wrapper around PRAW (Python Reddit API Wrapper) with rate limiting."""

    def __init__(self, config: RedditConfig):
        """Initialize Reddit client.

        Args:
            config: Reddit API configuration

        Raises:
            ValueError: If client initialization fails
        """
        self.config = config
        self.last_request_time = 0
        self.min_request_interval = 60 / config.rate_limit_per_minute

        try:
            self.reddit = praw.Reddit(
                client_id=config.client_id,
                client_secret=config.client_secret,
                user_agent=config.user_agent,
                username=config.username if config.username else None,
                password=config.password if config.password else None,
            )
            # Verify authentication only when credentials are provided
            if config.username and config.password:
                _ = self.reddit.user.me()
                logger.info("Successfully authenticated with Reddit API (user: %s)", config.username)
            else:
                logger.info("Initialized Reddit client in read-only mode")
        except PrawException as e:
            logger.error(f"Failed to authenticate with Reddit: {e}")
            raise ValueError("Reddit authentication failed") from e

    def _rate_limit(self) -> None:
        """Apply rate limiting to API requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def fetch_posts(
        self,
        subreddit_name: str,
        limit: int = 100,
        time_filter: str = "month",
        sort: str = "new",
    ) -> list[Submission]:
        """Fetch posts from a subreddit.

        Args:
            subreddit_name: Name of subreddit to fetch from
            limit: Maximum number of posts to fetch
            time_filter: Time filter for posts (hour, day, week, month, year, all)
            sort: Sort order (hot, new, top, rising, controversial)

        Returns:
            List of Reddit submissions

        Raises:
            ValueError: If subreddit doesn't exist or can't be accessed
        """
        try:
            self._rate_limit()
            subreddit = self.reddit.subreddit(subreddit_name)

            # Test subreddit access by getting subscribers
            _ = subreddit.subscribers
            logger.info(f"Fetching {limit} posts from r/{subreddit_name}")

            if sort == "top":
                posts = list(subreddit.top(time_filter=time_filter, limit=limit))
            elif sort == "controversial":
                posts = list(subreddit.controversial(time_filter=time_filter, limit=limit))
            elif sort == "hot":
                posts = list(subreddit.hot(limit=limit))
            else:  # new
                posts = list(subreddit.new(limit=limit))

            logger.info(f"Successfully fetched {len(posts)} posts from r/{subreddit_name}")
            return posts

        except PrawException as e:
            logger.error(f"Failed to fetch posts from r/{subreddit_name}: {e}")
            raise ValueError(f"Cannot access subreddit r/{subreddit_name}") from e

    def fetch_comments(
        self,
        submission: Submission,
        limit: int = 50,
    ) -> list[RedditComment]:
        """Fetch comments from a submission.

        Args:
            submission: PRAW submission object
            limit: Maximum number of comments to fetch

        Returns:
            List of RedditComment models

        Raises:
            ValueError: If comment fetching fails
        """
        try:
            self._rate_limit()

            # Discard "load more" stubs — only use already-loaded comments
            # (limit=None would expand every stub, making hundreds of extra API calls)
            submission.comments.replace_more(limit=0)

            comments = []
            for i, comment in enumerate(submission.comments.list()):
                if i >= limit:
                    break

                # Skip deleted or removed comments
                if comment.author is None:
                    continue

                try:
                    reddit_comment = RedditComment(
                        comment_id=comment.id,
                        post_id=submission.id,
                        author=comment.author.name,
                        text=comment.body,
                        score=comment.score,
                        created_at=datetime.fromtimestamp(comment.created_utc),
                        parent_comment_id=comment.parent_id.split("_")[1] if "_" in comment.parent_id else None,
                    )
                    comments.append(reddit_comment)
                except Exception as e:
                    logger.warning(f"Failed to process comment {comment.id}: {e}")
                    continue

            logger.info(f"Fetched {len(comments)} comments from post {submission.id}")
            return comments

        except PrawException as e:
            logger.error(f"Failed to fetch comments for post {submission.id}: {e}")
            raise ValueError(f"Cannot fetch comments for post {submission.id}") from e

    def submission_to_post(
        self,
        submission: Submission,
        comments: Optional[list[RedditComment]] = None,
    ) -> RedditPost:
        """Convert PRAW submission to RedditPost model.

        Args:
            submission: PRAW submission object
            comments: Optional list of comments to attach

        Returns:
            RedditPost model instance
        """
        return RedditPost(
            post_id=submission.id,
            title=submission.title,
            content=submission.selftext,
            author=submission.author.name if submission.author else "[deleted]",
            subreddit=submission.subreddit.display_name,
            score=submission.score,
            num_comments=submission.num_comments,
            created_at=datetime.fromtimestamp(submission.created_utc),
            url=submission.url,
            comments=comments or [],
        )

    def fetch_posts_with_comments(
        self,
        subreddit_name: str,
        posts_limit: int = 100,
        comments_limit: int = 50,
        time_filter: str = "month",
    ) -> list[RedditPost]:
        """Fetch posts with their comments.

        Args:
            subreddit_name: Name of subreddit to fetch from
            posts_limit: Maximum number of posts to fetch
            comments_limit: Maximum comments per post
            time_filter: Time filter for posts

        Returns:
            List of RedditPost models with comments
        """
        submissions = self.fetch_posts(
            subreddit_name=subreddit_name,
            limit=posts_limit,
            time_filter=time_filter,
        )

        posts = []
        for submission in submissions:
            try:
                comments = self.fetch_comments(submission, limit=comments_limit)
                post = self.submission_to_post(submission, comments)
                posts.append(post)
            except Exception as e:
                logger.warning(f"Failed to process post {submission.id}: {e}")
                continue

        logger.info(f"Successfully fetched {len(posts)} posts with comments from r/{subreddit_name}")
        return posts
