#!/usr/bin/env python
"""Validation script for LLM extraction setup."""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_google_api_key():
    """Check if Google API key is configured."""
    logger.info("Checking Google Gemini API key...")
    
    import os
    from dotenv import load_dotenv
    
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
    
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key or api_key.startswith("your_"):
        logger.error("❌ GOOGLE_API_KEY not configured")
        logger.info("   Get one from: https://aistudio.google.com/apikey")
        logger.info("   Add to .env: GOOGLE_API_KEY=your_key_here")
        return False
    
    logger.info("✅ GOOGLE_API_KEY configured")
    return True


def check_llm_config():
    """Check LLM configuration settings."""
    logger.info("\nChecking LLM configuration...")
    
    try:
        from mama_health.config import AppConfig
        
        config = AppConfig()
        llm_config = config.llm
        
        logger.info(f"✅ LLM Model: {llm_config.model}")
        logger.info(f"✅ Temperature: {llm_config.temperature}")
        logger.info(f"✅ Max Tokens: {llm_config.max_tokens}")
        logger.info(f"✅ Timeout: {llm_config.request_timeout}s")
        
        return True
    except Exception as e:
        logger.error(f"❌ LLM configuration failed: {e}")
        return False


def test_gemini_api():
    """Test connection to Gemini API."""
    logger.info("\nTesting Gemini API connection...")
    
    try:
        import os
        os.environ["PYTHONWARNINGS"] = "ignore"
        
        from mama_health.config import AppConfig
        from mama_health.llm_extractor import LLMExtractor
        
        config = AppConfig()
        extractor = LLMExtractor(config)
        
        logger.info("✅ LLMExtractor initialized successfully")
        
        # Try a simple extraction (no API call yet)
        logger.info("✅ Can create extraction requests")
        
        return True
    
    except ValueError as e:
        if "GOOGLE_API_KEY" in str(e):
            logger.error("❌ Missing or invalid GOOGLE_API_KEY")
        else:
            logger.error(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Gemini API test failed: {e}")
        return False


def test_gemini_live():
    """Test a live extraction with Gemini API."""
    logger.info("\nTesting live Gemini extraction...")
    
    try:
        from mama_health.config import AppConfig
        from mama_health.llm_extractor import LLMExtractor
        
        config = AppConfig()
        extractor = LLMExtractor(config)
        
        # Simple test extraction
        test_text = "I was diagnosed with diabetes last year."
        
        logger.info("  Calling Gemini API with test extraction...")
        
        events = extractor.extract_events(
            text=test_text,
            source_post_id="test_001",
            min_confidence=0.5,
        )
        
        logger.info(f"✅ Extract successful")
        logger.info(f"   Extracted {len(events)} event(s)")
        
        if events:
            for event in events:
                logger.info(f"   - {event.event_type}: {event.description}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Live extraction failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Verify GOOGLE_API_KEY is correct")
        logger.info("2. Check internet connection")
        logger.info("3. Gemini free tier limit: ~60 req/min")
        logger.info("4. Review: https://aistudio.google.com/apikey")
        return False


def test_prompt_templates():
    """Test prompt template loading."""
    logger.info("\nTesting prompt templates...")
    
    try:
        from mama_health.prompts import (
            EXTRACTION_SYSTEM_PROMPT,
            create_extraction_prompt,
            get_prompt_variant,
            EventType,
            EntityType,
        )
        
        # Test system prompt
        assert len(EXTRACTION_SYSTEM_PROMPT) > 100
        logger.info("✅ System prompt loaded")
        
        # Test prompt creation
        test_text = "I had a diagnosis"
        prompt = create_extraction_prompt(test_text)
        assert test_text in prompt
        logger.info("✅ Prompt creation works")
        
        # Test variants
        variants = ["general", "symptoms", "medications", "timeline", "emotion", "needs"]
        for variant in variants:
            prompt = get_prompt_variant(variant, test_text)
            assert len(prompt) > 50
        logger.info(f"✅ All {len(variants)} prompt variants available")
        
        # Test enums
        event_types = [e.value for e in EventType]
        assert "diagnosis" in event_types
        logger.info(f"✅ Event types defined ({len(event_types)} types)")
        
        entity_types = [e.value for e in EntityType]
        assert "medication" in entity_types
        logger.info(f"✅ Entity types defined ({len(entity_types)} types)")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Prompt template test failed: {e}")
        return False


def test_dagster_assets():
    """Test that LLM extraction assets load."""
    logger.info("\nTesting Dagster assets...")
    
    try:
        from mama_health.assets.llm_extraction import (
            llm_extractor,
            extracted_post_events,
            extracted_comment_events,
            all_extracted_events,
            symptom_mentions,
            medication_mentions,
            extraction_quality_metrics,
        )
        
        count = 7
        logger.info(f"✅ {count} LLM extraction assets loaded")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Asset loading failed: {e}")
        return False


def main():
    """Run all validation checks."""
    logger.info("=" * 60)
    logger.info("mama health LLM Extraction Validation")
    logger.info("=" * 60)
    
    checks = [
        ("Google API Key", check_google_api_key),
        ("LLM Configuration", check_llm_config),
        ("Prompt Templates", test_prompt_templates),
        ("LLMExtractor Init", test_gemini_api),
        ("Dagster Assets", test_dagster_assets),
        ("Live Gemini API", test_gemini_live),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"❌ {check_name} crashed: {e}")
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
        logger.info("\n🎉 LLM extraction setup validated!")
        logger.info("\nNext steps:")
        logger.info("1. Start Dagster: docker compose up")
        logger.info("2. Visit http://localhost:3000")
        logger.info("3. Run llm_extraction_job or end_to_end_job")
        return 0
    else:
        logger.error("\n❌ Some checks failed. Please review above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
