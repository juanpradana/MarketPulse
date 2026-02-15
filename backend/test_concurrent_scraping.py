"""
Test Concurrent Scraping Implementation

This script tests the ThreadPoolExecutor-based concurrent scraping
and compares timing with sequential execution.
"""

import time
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_import():
    """Test that scheduler module imports correctly."""
    print("\n" + "="*60)
    print("TEST 1: Module Import")
    print("="*60)
    try:
        from modules.scheduler import scrape_all_news, scrape_single_source
        print("[OK] Scheduler module imported successfully")
        print(f"[OK] scrape_single_source function: {scrape_single_source}")
        print(f"[OK] scrape_all_news function: {scrape_all_news}")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False


def test_single_scraper():
    """Test scraping a single source."""
    print("\n" + "="*60)
    print("TEST 2: Single Source Scraping (CNBC)")
    print("="*60)
    try:
        from modules.scheduler import scrape_single_source

        start = time.time()
        result = scrape_single_source("CNBC Indonesia", "modules.scraper_cnbc")
        elapsed = time.time() - start

        print(f"[OK] Scraped in {elapsed:.1f} seconds")
        print(f"[OK] Status: {result['status']}")
        print(f"[OK] Records scraped: {len(result.get('result', []))}")
        return True
    except Exception as e:
        print(f"[FAIL] Single scraper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_concurrent_scraping():
    """Test concurrent scraping with all sources."""
    print("\n" + "="*60)
    print("TEST 3: Concurrent Scraping (All Sources)")
    print("="*60)
    try:
        from modules.scheduler import scrape_all_news

        print("Starting concurrent scraping...")
        print("This will run 5 scrapers in parallel:")
        print("  - CNBC Indonesia")
        print("  - EmitenNews")
        print("  - Bisnis.com")
        print("  - Investor.id")
        print("  - Bloomberg Technoz")
        print()

        start = time.time()
        results = scrape_all_news()
        elapsed = time.time() - start

        print()
        print("="*60)
        print(f"RESULTS - Total Time: {elapsed:.1f} seconds")
        print("="*60)

        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = len(results) - success_count

        print(f"Successful: {success_count}/{len(results)}")
        print(f"Failed: {failed_count}/{len(results)}")
        print()

        # Individual results
        print("Individual Scraper Performance:")
        print("-" * 60)
        for r in results:
            status_icon = "[OK]" if r['status'] == 'success' else "[FAIL]"
            source = r['source']
            elapsed_time = r.get('elapsed_seconds', 0)
            error = r.get('error', '')

            if r['status'] == 'success':
                records = len(r.get('result', []))
                print(f"{status_icon} {source:20s} | {elapsed_time:5.1f}s | {records} records")
            else:
                print(f"{status_icon} {source:20s} | {elapsed_time:5.1f}s | ERROR: {error[:30]}")

        return success_count > 0

    except Exception as e:
        print(f"[FAIL] Concurrent scraping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sequential_vs_concurrent():
    """Compare sequential vs concurrent execution."""
    print("\n" + "="*60)
    print("TEST 4: Sequential vs Concurrent Comparison")
    print("="*60)

    sources = [
        ("CNBC Indonesia", "modules.scraper_cnbc"),
        ("EmitenNews", "modules.scraper_emiten"),
    ]

    # Test sequential
    print("\nSequential execution (2 sources):")
    from modules.scheduler import scrape_single_source

    seq_start = time.time()
    for name, path in sources:
        scrape_single_source(name, path)
    seq_elapsed = time.time() - seq_start
    print(f"Sequential time: {seq_elapsed:.1f}s")

    # Test concurrent (same 2 sources)
    print("\nConcurrent execution (2 sources):")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    con_start = time.time()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(scrape_single_source, name, path) for name, path in sources]
        for future in as_completed(futures):
            future.result()
    con_elapsed = time.time() - con_start
    print(f"Concurrent time: {con_elapsed:.1f}s")

    # Comparison
    print("\n" + "="*60)
    print(f"Sequential: {seq_elapsed:.1f}s")
    print(f"Concurrent: {con_elapsed:.1f}s")
    if con_elapsed < seq_elapsed:
        improvement = (seq_elapsed - con_elapsed) / seq_elapsed * 100
        print(f"[OK] Concurrent is {improvement:.0f}% faster")
    else:
        print("⚠ No speed improvement (may be due to testing environment)")

    return True


def test_scheduler_status():
    """Test scheduler status endpoint."""
    print("\n" + "="*60)
    print("TEST 5: Scheduler Status")
    print("="*60)
    try:
        from modules.scheduler import get_job_status

        status = get_job_status()
        print(f"[OK] Scheduler running: {status['running']}")
        print(f"[OK] Active jobs: {status['job_count']}")

        for job in status['jobs']:
            print(f"  - {job['name']}: {job['trigger']}")

        return True
    except Exception as e:
        print(f"[FAIL] Status check failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CONCURRENT SCRAPING TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("Import Test", test_import),
        ("Single Scraper", test_single_scraper),
        ("Concurrent Scraping", test_concurrent_scraping),
        ("Sequential vs Concurrent", test_sequential_vs_concurrent),
        ("Scheduler Status", test_scheduler_status),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n[FAIL] Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, success in results:
        status = "[OK] PASS" if success else "[FAIL] FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
