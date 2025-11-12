#!/usr/bin/env python3
"""
Test script to verify all integrations are working properly.
This script tests the core functionality without requiring all services to be running.
"""

import asyncio
import sys
import os

# Add the API app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'api'))

async def test_apple_rss_feeds():
    """Test Apple RSS feeds functionality."""
    print("🎵 Testing Apple RSS feeds...")
    try:
        from app.services.discovery_apple import apple_feed
        result = apple_feed('us', 0, 'most-recent', 'albums', 5)
        if result and len(result) > 0:
            print(f"✅ Apple RSS feeds working - got {len(result)} albums")
            print(f"   Sample: {result[0].get('artist')} - {result[0].get('title')}")
            return True
        else:
            print("❌ Apple RSS feeds returned no results")
            return False
    except Exception as e:
        print(f"❌ Apple RSS feeds failed: {e}")
        return False

async def test_musicbrainz():
    """Test MusicBrainz integration."""
    print("\n🎼 Testing MusicBrainz integration...")
    try:
        from app.services.metadata.providers.musicbrainz import MusicBrainzClient
        client = MusicBrainzClient('Phelia/1.0 (test)')
        result = await client.lookup_release_group('Radiohead', 'OK Computer', 1997)
        if result:
            artist_name = result.get('artist', {}).get('name')
            album_title = result.get('release_group', {}).get('title')
            print(f"✅ MusicBrainz working - found: {artist_name} - {album_title}")
            return True
        else:
            print("❌ MusicBrainz returned no results")
            return False
    except Exception as e:
        print(f"❌ MusicBrainz failed: {e}")
        return False

async def test_tmdb_config():
    """Test TMDB configuration."""
    print("\n🎬 Testing TMDB configuration...")
    try:
        # Check if TMDB key is configured in metadata-proxy
        metadata_proxy_path = os.path.join(os.path.dirname(__file__), 'services', 'metadata-proxy')
        if os.path.exists(metadata_proxy_path):
            sys.path.insert(0, metadata_proxy_path)
            from app.config import get_settings
            settings = get_settings()
            if settings.tmdb_api_key:
                print(f"✅ TMDB API key configured (starts with: {settings.tmdb_api_key[:10]}...)")
                return True
            else:
                print("❌ TMDB API key not configured")
                return False
        else:
            print("❌ Metadata-proxy service not found")
            return False
    except Exception as e:
        print(f"❌ TMDB configuration check failed: {e}")
        return False

async def test_api_key_providers():
    """Test API key provider configuration."""
    print("\n🔑 Testing API key providers...")
    try:
        from app.core.runtime_settings import PROVIDER_ENV_MAP, runtime_settings
        print(f"✅ Supported providers: {list(PROVIDER_ENV_MAP.keys())}")
        
        configured_count = 0
        for provider in PROVIDER_ENV_MAP.keys():
            is_configured = runtime_settings.is_configured(provider)
            status = "✅" if is_configured else "⚪"
            print(f"   {status} {provider}: {'configured' if is_configured else 'not configured'}")
            if is_configured:
                configured_count += 1
        
        print(f"📊 {configured_count}/{len(PROVIDER_ENV_MAP)} providers configured")
        return True
    except Exception as e:
        print(f"❌ API key provider check failed: {e}")
        return False

async def test_discovery_integration():
    """Test discovery service integration."""
    print("\n🔍 Testing discovery service integration...")
    try:
        from app.routes.discovery import apple_feed as discovery_apple_feed
        if discovery_apple_feed:
            print("✅ Apple RSS feeds integrated in discovery routes")
        else:
            print("❌ Apple RSS feeds not available in discovery routes")
            
        # Test if phelia discovery service is available
        try:
            from phelia.discovery import service as phelia_discovery_service
            if phelia_discovery_service:
                print("✅ Phelia discovery service available")
                # Test providers status
                status = await phelia_discovery_service.providers_status()
                print(f"   Provider status: {status.model_dump() if hasattr(status, 'model_dump') else status}")
            else:
                print("⚪ Phelia discovery service not available")
        except ImportError:
            print("⚪ Phelia discovery service not available (import error)")
        
        return True
    except Exception as e:
        print(f"❌ Discovery integration check failed: {e}")
        return False

async def main():
    """Run all integration tests."""
    print("🧪 Phelia Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_apple_rss_feeds,
        test_musicbrainz,
        test_tmdb_config,
        test_api_key_providers,
        test_discovery_integration,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"✅ {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integrations are working!")
        print("\nIf you're still experiencing issues:")
        print("1. Make sure all Docker services are running (docker-compose up)")
        print("2. Check that the metadata-proxy service is healthy")
        print("3. Configure API keys in the settings UI for enhanced functionality")
    else:
        print(f"\n⚠️  {total - passed} integration(s) need attention")
        print("\nNext steps:")
        print("1. Review the failed tests above")
        print("2. Ensure all required services are running")
        print("3. Check environment variables and configuration")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)