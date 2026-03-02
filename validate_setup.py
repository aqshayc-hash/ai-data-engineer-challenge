#!/usr/bin/env python
"""Validation script for Reddit ingestion setup."""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_environment_variables():
    """Check if required environment variables are set."""
    logger.info("Checking environment variables...")
    
    import os
    from dotenv import load_dotenv
    
    # Load .env file
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        logger.error(f"❌ .env file not found at {env_path}")
        logger.info(f"   Create it with: cp .env.example .env")
        return False
    
    load_dotenv(env_path)
    
    required_vars = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith("your_"):
            missing.append(var)
            logger.warning(f"⚠️  {var} not configured")
        else:
            logger.info(f"✅ {var} configured")
    
    if missing:
        logger.error(f"\n❌ Missing or invalid environment variables:")
        for var in missing:
            logger.error(f"   - {var}")
        return False
    
    return True


def check_dependencies():
    """Check if required packages are installed."""
    logger.info("\nChecking dependencies...")
    
    required_packages = [
        ("dagster", "Dagster"),
        ("praw", "PRAW"),
        ("pydantic", "Pydantic"),
        ("dotenv", "python-dotenv"),
        ("litellm", "litellm"),
    ]
    
    missing = []
    for package, name in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {name} installed")
        except ImportError:
            missing.append(name)
            logger.warning(f"⚠️  {name} NOT installed")
    
    if missing:
        logger.error(f"\n❌ Missing packages:")
        for name in missing:
            logger.error(f"   - {name}")
        logger.info("\nInstall with: uv sync")
        return False
    
    return True


def test_reddit_authentication():
    """Test Reddit API authentication."""
    logger.info("\nTesting Reddit API authentication...")
    
    try:
        from mama_health.config import AppConfig
        from mama_health.reddit_client import RedditClient
        
        config = AppConfig()
        client = RedditClient(config.reddit)
        
        logger.info("✅ Reddit authentication successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Reddit authentication failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
        logger.info("2. Verify they are from https://www.reddit.com/prefs/apps")
        logger.info("3. Ensure REDDIT_USER_AGENT is set")
        logger.info("4. See REDDIT_INGESTION.md for detailed setup")
        return False


def test_subreddit_access():
    """Test access to configured subreddit."""
    logger.info("\nTesting subreddit access...")
    
    try:
        from mama_health.config import AppConfig
        from mama_health.reddit_client import RedditClient
        
        config = AppConfig()
        client = RedditClient(config.reddit)
        
        logger.info(f"Attempting to access r/{config.pipeline.target_subreddit}...")
        
        posts = client.fetch_posts(
            subreddit_name=config.pipeline.target_subreddit,
            limit=5,
        )
        
        logger.info(f"✅ Successfully accessed r/{config.pipeline.target_subreddit}")
        logger.info(f"   Retrieved {len(posts)} sample posts")
        
        if posts:
            first_post = posts[0]
            logger.info(f"   Sample post: '{first_post.title[:60]}...'")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Subreddit access failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check TARGET_SUBREDDIT in .env")
        logger.info("2. Verify the subreddit is public and exists")
        logger.info("3. Check reddit authentication (test_reddit_authentication)")
        return False


def test_dagster_definitions():
    """Test that Dagster definitions load correctly."""
    logger.info("\nTesting Dagster definitions...")
    
    try:
        from mama_health.dagster_definitions import defs
        
        assets = defs.assets if hasattr(defs, 'assets') else []
        jobs = defs.jobs if hasattr(defs, 'jobs') else []
        
        logger.info(f"✅ Dagster definitions loaded")
        logger.info(f"   Assets: {len(assets)}")
        logger.info(f"   Jobs: {len(jobs)}")
        
        if jobs:
            logger.info(f"   Available jobs:")
            for job in jobs:
                logger.info(f"     - {job.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Dagster definitions failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check src/mama_health/dagster_definitions.py syntax")
        logger.info("2. Verify all imports are available")
        return False


def main():
    """Run all validation checks."""
    logger.info("=" * 60)
    logger.info("mama health Reddit Ingestion Validation")
    logger.info("=" * 60)
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Dependencies", check_dependencies),
        ("Dagster Definitions", test_dagster_definitions),
        ("Reddit Authentication", test_reddit_authentication),
        ("Subreddit Access", test_subreddit_access),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"❌ {check_name} check crashed: {e}")
            results.append((check_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅" if result else "❌"
        logger.info(f"{status} {check_name}")
    
    logger.info(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        logger.info("\n🎉 All validation checks passed!")
        logger.info("\nNext steps:")
        logger.info("1. Start Dagster: docker compose up")
        logger.info("2. Visit http://localhost:3000")
        logger.info("3. Trigger reddit_ingestion_job")
        return 0
    else:
        logger.error("\n❌ Some checks failed. Please review above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
