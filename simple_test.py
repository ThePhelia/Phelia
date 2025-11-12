#!/usr/bin/env python3
"""
Simple test to verify core functionality without full environment setup.
"""

import asyncio
import sys
import os

# Add the API app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'api'))

async def test_apple_rss():
    """Test Apple RSS feeds."""
    print("Testing Apple RSS feeds...")
    try:
        from app.services.discovery_apple import apple_feed
        result = apple_feed('us', 0, 'most-recent', 'albums', 3)
        print(f"✅ Apple RSS: {len(result)} albums found")
        if result:
            for i, album in enumerate(result[:2]):
                print(f"   {i+1}. {album.get('artist')} - {album.get('title')}")
        return True
    except Exception as e:
        print(f"❌ Apple RSS failed: {e}")
        return False

async def test_musicbrainz_direct():
    """Test MusicBrainz directly without config."""
    print("\nTesting MusicBrainz directly...")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://musicbrainz.org/ws/2/release-group",
                params={
                    "query": 'release:"OK Computer" AND artist:"Radiohead"',
                    "fmt": "json",
                    "limit": "1"
                },
                headers={"User-Agent": "Phelia/1.0 (test)"}
            )
            if resp.status_code == 200:
                data = resp.json()
                groups = data.get("release-groups", [])
                if groups:
                    group = groups[0]
                    artist = (group.get("artist-credit") or [{}])[0].get("name", "Unknown")
                    title = group.get("title", "Unknown")
                    print(f"✅ MusicBrainz: Found {artist} - {title}")
                    return True
                else:
                    print("❌ MusicBrainz: No results found")
                    return False
            else:
                print(f"❌ MusicBrainz: HTTP {resp.status_code}")
                return False
    except Exception as e:
        print(f"❌ MusicBrainz failed: {e}")
        return False

async def test_tmdb_direct():
    """Test TMDB directly."""
    print("\nTesting TMDB directly...")
    try:
        import httpx
        # Use the hardcoded API key from metadata-proxy config
        api_key = "71654942f10fb51fe2d66a1f756b4311"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.themoviedb.org/3/search/movie",
                params={
                    "api_key": api_key,
                    "query": "The Matrix",
                    "year": 1999
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    movie = results[0]
                    title = movie.get("title", "Unknown")
                    year = movie.get("release_date", "")[:4]
                    print(f"✅ TMDB: Found {title} ({year})")
                    return True
                else:
                    print("❌ TMDB: No results found")
                    return False
            else:
                print(f"❌ TMDB: HTTP {resp.status_code}")
                return False
    except Exception as e:
        print(f"❌ TMDB failed: {e}")
        return False

async def main():
    """Run simple tests."""
    print("🧪 Simple Integration Tests")
    print("=" * 40)
    
    tests = [
        test_apple_rss,
        test_musicbrainz_direct,
        test_tmdb_direct,
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All core integrations working!")
        print("\nThe issues you reported might be:")
        print("1. Services not running in Docker environment")
        print("2. Missing API keys for optional providers")
        print("3. Frontend not displaying data correctly")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)