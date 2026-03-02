"""Tests for Reddit ingestion."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from mama_health.models import RedditComment, RedditPost
from mama_health.reddit_client import RedditClient
from mama_health.config import RedditConfig


@pytest.fixture
def reddit_config():
    """Provide test Reddit configuration."""
    return RedditConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        user_agent="test-agent/1.0",
    )


def test_reddit_comment_model():
    """Test RedditComment model validation."""
    comment = RedditComment(
        comment_id="c123",
        post_id="p123",
        author="test_user",
        text="Test comment",
        score=10,
        created_at=datetime.now(),
    )
    
    assert comment.comment_id == "c123"
    assert comment.post_id == "p123"
    assert comment.author == "test_user"
    assert comment.score == 10


def test_reddit_post_model():
    """Test RedditPost model validation."""
    post = RedditPost(
        post_id="p123",
        title="Test Post",
        content="Test content",
        author="test_user",
        subreddit="test_subreddit",
        score=100,
        num_comments=5,
        created_at=datetime.now(),
        url="https://reddit.com/r/test/123",
    )
    
    assert post.post_id == "p123"
    assert post.title == "Test Post"
    assert len(post.comments) == 0


def test_reddit_post_with_comments():
    """Test RedditPost model with comments."""
    comment = RedditComment(
        comment_id="c123",
        post_id="p123",
        author="commenter",
        text="Great post",
        score=5,
        created_at=datetime.now(),
    )
    
    post = RedditPost(
        post_id="p123",
        title="Test Post",
        content="Test content",
        author="test_user",
        subreddit="test_subreddit",
        score=100,
        num_comments=1,
        created_at=datetime.now(),
        url="https://reddit.com/r/test/123",
        comments=[comment],
    )
    
    assert len(post.comments) == 1
    assert post.comments[0].author == "commenter"


@patch('mama_health.reddit_client.praw.Reddit')
def test_reddit_client_initialization(mock_reddit_class, reddit_config):
    """Test RedditClient initialization."""
    mock_reddit = MagicMock()
    mock_reddit.user.me.return_value = MagicMock(name="test_user")
    mock_reddit_class.return_value = mock_reddit
    
    client = RedditClient(reddit_config)
    
    assert client is not None
    assert client.config == reddit_config
    mock_reddit_class.assert_called_once()


@patch('mama_health.reddit_client.praw.Reddit')
def test_reddit_client_authentication_failure(mock_reddit_class, reddit_config):
    """Test RedditClient raises error on auth failure."""
    from praw.exceptions import ClientException
    
    mock_reddit_class.side_effect = ClientException("Invalid credentials")
    
    with pytest.raises(ValueError, match="Reddit authentication failed"):
        RedditClient(reddit_config)


def test_rate_limiting():
    """Test rate limiting mechanism."""
    config = RedditConfig(
        client_id="test",
        client_secret="test",
        user_agent="test",
        rate_limit_per_minute=120,  # 0.5s between requests
    )
    
    with patch('mama_health.reddit_client.praw.Reddit'):
        client = RedditClient(config)
        
        # Min interval should be 60/120 = 0.5 seconds
        assert client.min_request_interval == 0.5
