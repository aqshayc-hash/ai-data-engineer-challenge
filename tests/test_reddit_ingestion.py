"""Tests for Reddit ingestion."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from mama_health.assets.reddit_ingestion import _load_checkpoint, _save_checkpoint
from mama_health.config import RedditConfig
from mama_health.models import RedditComment, RedditPost
from mama_health.reddit_client import RedditClient


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


@patch("mama_health.reddit_client.praw.Reddit")
def test_reddit_client_initialization(mock_reddit_class, reddit_config):
    """Test RedditClient initialization."""
    mock_reddit = MagicMock()
    mock_reddit.user.me.return_value = MagicMock(name="test_user")
    mock_reddit_class.return_value = mock_reddit

    client = RedditClient(reddit_config)

    assert client is not None
    assert client.config == reddit_config
    mock_reddit_class.assert_called_once()


@patch("mama_health.reddit_client.praw.Reddit")
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

    with patch("mama_health.reddit_client.praw.Reddit"):
        client = RedditClient(config)

        # Min interval should be 60/120 = 0.5 seconds
        assert client.min_request_interval == 0.5


# ===== Checkpoint helper tests =====


def test_load_checkpoint_no_file(tmp_path, monkeypatch):
    """Returns None when checkpoint file does not exist."""
    monkeypatch.chdir(tmp_path)
    result = _load_checkpoint()
    assert result is None


def test_save_and_load_checkpoint(tmp_path, monkeypatch):
    """Saved checkpoint can be read back correctly."""
    monkeypatch.chdir(tmp_path)
    ts = datetime(2025, 6, 15, 12, 0, 0)
    _save_checkpoint(ts)
    loaded = _load_checkpoint()
    assert loaded == ts


def test_load_checkpoint_corrupted_file(tmp_path, monkeypatch):
    """Returns None gracefully when checkpoint file is corrupted."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".ingestion_checkpoint.json").write_text("not valid json")
    result = _load_checkpoint()
    assert result is None


def test_save_checkpoint_creates_file(tmp_path, monkeypatch):
    """Saving a checkpoint writes a JSON file with the expected key."""
    monkeypatch.chdir(tmp_path)
    ts = datetime(2025, 1, 1, 0, 0, 0)
    _save_checkpoint(ts)
    checkpoint_file = tmp_path / ".ingestion_checkpoint.json"
    assert checkpoint_file.exists()
    data = json.loads(checkpoint_file.read_text())
    assert "last_ingested_at" in data
    assert data["last_ingested_at"] == ts.isoformat()


# ===== RedditClient.__init__ read-only mode =====


@patch("mama_health.reddit_client.praw.Reddit")
def test_reddit_client_readonly_mode_skips_user_me(mock_reddit_class):
    """Client in read-only mode (no username) must NOT call user.me()."""
    mock_reddit = MagicMock()
    mock_reddit_class.return_value = mock_reddit

    # Pass empty strings explicitly so .env values don't leak in via BaseSettings
    config = RedditConfig(
        client_id="fake_id",
        client_secret="fake_secret",
        user_agent="test/1.0",
        username="",
        password="",
    )
    client = RedditClient(config)

    assert client is not None
    mock_reddit.user.me.assert_not_called()


# ===== RedditClient._rate_limit =====


@patch("mama_health.reddit_client.praw.Reddit")
def test_rate_limit_sleeps_when_too_fast(mock_reddit_class, monkeypatch):
    """_rate_limit should call time.sleep() when requests arrive too quickly."""
    mock_reddit_class.return_value = MagicMock()

    config = RedditConfig(
        client_id="x",
        client_secret="x",
        user_agent="x",
        rate_limit_per_minute=60,  # 1-second interval
    )
    client = RedditClient(config)

    sleep_calls = []
    monkeypatch.setattr("mama_health.reddit_client.time.sleep", lambda s: sleep_calls.append(s))

    # Simulate last request was only 0.1 s ago → should sleep ~0.9 s
    with patch("mama_health.reddit_client.time.time", side_effect=[0.1, 1.0]):
        client.last_request_time = 0.0
        client._rate_limit()

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == pytest.approx(0.9, abs=0.01)


@patch("mama_health.reddit_client.praw.Reddit")
def test_rate_limit_no_sleep_when_interval_satisfied(mock_reddit_class, monkeypatch):
    """_rate_limit should NOT sleep when enough time has elapsed."""
    mock_reddit_class.return_value = MagicMock()

    config = RedditConfig(
        client_id="x",
        client_secret="x",
        user_agent="x",
        rate_limit_per_minute=60,
    )
    client = RedditClient(config)

    sleep_calls = []
    monkeypatch.setattr("mama_health.reddit_client.time.sleep", lambda s: sleep_calls.append(s))

    # Simulate last request was 2 s ago — interval (1 s) already satisfied
    with patch("mama_health.reddit_client.time.time", side_effect=[2.0, 2.0]):
        client.last_request_time = 0.0
        client._rate_limit()

    assert sleep_calls == []


# ===== RedditClient.fetch_posts — all 4 sort modes =====


@pytest.mark.parametrize(
    "sort,praw_method",
    [
        ("new", "new"),
        ("hot", "hot"),
        ("top", "top"),
        ("controversial", "controversial"),
    ],
)
@patch("mama_health.reddit_client.praw.Reddit")
def test_fetch_posts_sort_modes(mock_reddit_class, sort, praw_method, mock_submission):
    """fetch_posts calls the correct PRAW listing method for each sort value."""
    mock_reddit = MagicMock()
    mock_reddit_class.return_value = mock_reddit

    mock_subreddit = MagicMock()
    mock_subreddit.subscribers = 10000
    getattr(mock_subreddit, praw_method).return_value = [mock_submission]
    mock_reddit.subreddit.return_value = mock_subreddit

    config = RedditConfig(client_id="x", client_secret="x", user_agent="x")
    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        client = RedditClient(config)
        client.last_request_time = 0.0  # skip sleep

    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        with patch("mama_health.reddit_client.time.sleep"):
            posts = client.fetch_posts("Crohns", sort=sort)

    assert len(posts) == 1
    getattr(mock_subreddit, praw_method).assert_called_once()


@patch("mama_health.reddit_client.praw.Reddit")
def test_fetch_posts_raises_on_inaccessible_subreddit(mock_reddit_class):
    """fetch_posts raises ValueError when subreddit access fails."""
    from praw.exceptions import PRAWException

    mock_reddit = MagicMock()
    mock_reddit_class.return_value = mock_reddit

    mock_subreddit = MagicMock()
    # Accessing .subscribers raises PRAWException
    type(mock_subreddit).subscribers = property(
        lambda self: (_ for _ in ()).throw(PRAWException("forbidden"))
    )
    mock_reddit.subreddit.return_value = mock_subreddit

    config = RedditConfig(client_id="x", client_secret="x", user_agent="x")
    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        client = RedditClient(config)
        client.last_request_time = 0.0

    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        with patch("mama_health.reddit_client.time.sleep"):
            with pytest.raises(ValueError, match="Cannot access subreddit"):
                client.fetch_posts("nonexistent_sub")


# ===== RedditClient.fetch_comments =====


@patch("mama_health.reddit_client.praw.Reddit")
def test_fetch_comments_skips_deleted_author(mock_reddit_class, mock_submission):
    """Comments with author=None (deleted) must be silently skipped."""
    mock_reddit_class.return_value = MagicMock()

    # Two comments: one deleted, one valid
    deleted_comment = MagicMock()
    deleted_comment.author = None

    valid_comment = MagicMock()
    valid_comment.id = "c001"
    valid_comment.author = MagicMock()
    valid_comment.author.name = "real_user"
    valid_comment.body = "Helpful comment"
    valid_comment.score = 5
    valid_comment.created_utc = 1704067200.0
    valid_comment.parent_id = "t3_abc123"

    mock_submission.comments.list.return_value = [deleted_comment, valid_comment]

    config = RedditConfig(client_id="x", client_secret="x", user_agent="x")
    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        client = RedditClient(config)
        client.last_request_time = 0.0

    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        with patch("mama_health.reddit_client.time.sleep"):
            comments = client.fetch_comments(mock_submission)

    assert len(comments) == 1
    assert comments[0].author == "real_user"


@patch("mama_health.reddit_client.praw.Reddit")
def test_fetch_comments_construction_error_skipped(mock_reddit_class, mock_submission):
    """Comments that fail RedditComment() construction are skipped gracefully."""
    mock_reddit_class.return_value = MagicMock()

    bad_comment = MagicMock()
    bad_comment.author = MagicMock()
    bad_comment.author.name = "user"
    bad_comment.id = "bad"
    bad_comment.body = "text"
    bad_comment.score = 1
    bad_comment.created_utc = 1704067200.0
    # parent_id without underscore — maps to parent_comment_id=None (valid)
    bad_comment.parent_id = "no_underscore"  # actually this is fine; force error differently
    # Make .score raise to trigger the except block
    type(bad_comment).score = property(lambda self: (_ for _ in ()).throw(ValueError("bad score")))

    good_comment = MagicMock()
    good_comment.id = "g001"
    good_comment.author = MagicMock()
    good_comment.author.name = "good_user"
    good_comment.body = "Good comment"
    good_comment.score = 3
    good_comment.created_utc = 1704067200.0
    good_comment.parent_id = "t1_parent1"

    mock_submission.comments.list.return_value = [bad_comment, good_comment]

    config = RedditConfig(client_id="x", client_secret="x", user_agent="x")
    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        client = RedditClient(config)
        client.last_request_time = 0.0

    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        with patch("mama_health.reddit_client.time.sleep"):
            comments = client.fetch_comments(mock_submission)

    assert len(comments) == 1
    assert comments[0].author == "good_user"


@pytest.mark.parametrize(
    "parent_id,expected",
    [
        ("t1_abc123", "abc123"),  # standard parent comment reference
        ("abc123", None),  # no underscore → no parent comment
    ],
)
@patch("mama_health.reddit_client.praw.Reddit")
def test_fetch_comments_parent_id_parsing(mock_reddit_class, mock_submission, parent_id, expected):
    """parent_id string is parsed correctly into parent_comment_id."""
    mock_reddit_class.return_value = MagicMock()

    comment = MagicMock()
    comment.id = "c001"
    comment.author = MagicMock()
    comment.author.name = "user"
    comment.body = "text"
    comment.score = 1
    comment.created_utc = 1704067200.0
    comment.parent_id = parent_id

    mock_submission.comments.list.return_value = [comment]

    config = RedditConfig(client_id="x", client_secret="x", user_agent="x")
    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        client = RedditClient(config)
        client.last_request_time = 0.0

    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        with patch("mama_health.reddit_client.time.sleep"):
            comments = client.fetch_comments(mock_submission)

    assert len(comments) == 1
    assert comments[0].parent_comment_id == expected


# ===== RedditClient.submission_to_post =====


@patch("mama_health.reddit_client.praw.Reddit")
def test_submission_to_post_deleted_author(mock_reddit_class, mock_submission):
    """submission_to_post uses '[deleted]' when author is None."""
    mock_reddit_class.return_value = MagicMock()
    mock_submission.author = None

    config = RedditConfig(client_id="x", client_secret="x", user_agent="x")
    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        client = RedditClient(config)

    post = client.submission_to_post(mock_submission)
    assert post.author == "[deleted]"


@patch("mama_health.reddit_client.praw.Reddit")
def test_submission_to_post_no_comments_defaults_empty(mock_reddit_class, mock_submission):
    """submission_to_post with comments=None returns post with empty comments list."""
    mock_reddit_class.return_value = MagicMock()

    config = RedditConfig(client_id="x", client_secret="x", user_agent="x")
    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        client = RedditClient(config)

    post = client.submission_to_post(mock_submission, comments=None)
    assert post.comments == []


# ===== RedditClient.fetch_posts_with_comments =====


@patch("mama_health.reddit_client.praw.Reddit")
def test_fetch_posts_with_comments_skips_erroring_post(mock_reddit_class, mock_submission):
    """fetch_posts_with_comments skips a post that errors during fetch_comments."""
    mock_reddit_class.return_value = MagicMock()

    config = RedditConfig(client_id="x", client_secret="x", user_agent="x")
    with patch("mama_health.reddit_client.time.time", return_value=9999.0):
        client = RedditClient(config)

    sub_a = MagicMock()
    sub_a.id = "ok1"
    sub_b = MagicMock()
    sub_b.id = "bad"
    sub_c = MagicMock()
    sub_c.id = "ok2"

    def fake_fetch_posts(**kwargs):
        return [sub_a, sub_b, sub_c]

    def fake_fetch_comments(submission, limit=50):
        if submission.id == "bad":
            raise ValueError("comment fetch failed")
        return []

    def fake_submission_to_post(submission, comments=None):
        from mama_health.models import RedditPost

        return RedditPost(
            post_id=submission.id,
            title="title",
            content="text",
            author="user",
            subreddit="Crohns",
            score=1,
            num_comments=0,
            created_at=datetime(2024, 1, 1),
            url="https://reddit.com/r/Crohns/1",
            comments=comments or [],
        )

    client.fetch_posts = fake_fetch_posts
    client.fetch_comments = fake_fetch_comments
    client.submission_to_post = fake_submission_to_post

    posts = client.fetch_posts_with_comments("Crohns")

    assert len(posts) == 2
    post_ids = {p.post_id for p in posts}
    assert "ok1" in post_ids
    assert "ok2" in post_ids
    assert "bad" not in post_ids
