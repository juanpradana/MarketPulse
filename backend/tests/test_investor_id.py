"""Quick test script for investor.id website analysis"""
import os
import pytest
import requests
from bs4 import BeautifulSoup


@pytest.mark.network
def test_investor_id():
    if os.getenv("ALLOW_NETWORK_TESTS") != "1":
        pytest.skip("Network tests disabled. Set ALLOW_NETWORK_TESTS=1 to run.")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://investor.id/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
    }

    # Test index page
    print('=== Testing Index Page ===')
    resp = requests.get('https://investor.id/corporate-action/indeks', headers=headers, timeout=15)
    print(f'Status: {resp.status_code}')
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/market/' in href or '/corporate-action/' in href:
            if href not in links and 'indeks' not in href:
                links.append(href)
    print(f'Found {len(links)} article links')
    for link in links[:5]:
        print(f'  - {link}')

    # Test article detail page
    print('\n\n=== Testing Article Detail Page ===')
    resp2 = requests.get('https://investor.id/market/425815/bumi-ungkap-aksi-baru', headers=headers, timeout=15)
    print(f'Status: {resp2.status_code}')
    soup2 = BeautifulSoup(resp2.text, 'html.parser')
    h1 = soup2.find('h1')
    print(f"Title: {h1.text.strip() if h1 else 'NOT FOUND'}")
    print('\nContent Samples:')
    for p in soup2.find_all('p')[:5]:
        text = p.get_text(strip=True)
        if text and len(text) > 50:
            print(f'  - {text[:80]}...')


if __name__ == "__main__":
    test_investor_id()
