"""Test Story Finder API endpoint"""
import os
import pytest
import requests

url = "http://localhost:8000/api/story-finder"
params = {
    "keywords": "right issue,akuisisi,dividen"
}


@pytest.mark.live_api
def test_story_finder_api():
    if os.getenv("ALLOW_LIVE_API_TESTS") != "1":
        pytest.skip("Live API tests disabled. Set ALLOW_LIVE_API_TESTS=1 to run.")

    print("Testing Story Finder API...")
    r = requests.get(url, params=params, timeout=15)

    if r.status_code == 200:
        d = r.json()
        print(f"Total: {d.get('total', 0)}")
        print(f"Stats: {d.get('keyword_stats', {})}")
        print("\nTop 5 Stories:")
        for s in d.get('stories', [])[:5]:
            print(f"  [{s['primary_icon']}] {s['ticker']}: {s['title'][:50]}...")
    else:
        print(f"Error: {r.status_code}")
        print(r.text)


if __name__ == "__main__":
    test_story_finder_api()
