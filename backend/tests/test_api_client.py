"""Quick test for NeoBDM API Client."""
import asyncio
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.neobdm_api_client import NeoBDMApiClient


async def test_all():
    client = NeoBDMApiClient()
    
    try:
        # 1. Test Login
        print("=" * 60)
        print("TEST 1: Login")
        t0 = time.time()
        ok = await client.login()
        print(f"  Login: {ok} ({time.time()-t0:.2f}s)")
        if not ok:
            print("  FAILED - cannot continue")
            return
        
        # 2. Test Market Summary
        print("\n" + "=" * 60)
        print("TEST 2: Market Summary (method=m, period=d)")
        t0 = time.time()
        df, ref_date = await client.get_market_summary(method='m', period='d')
        elapsed = time.time() - t0
        if df is not None:
            print(f"  OK: {len(df)} rows, date={ref_date} ({elapsed:.2f}s)")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Sample: {df.head(3).to_dict('records')}")
        else:
            print(f"  FAILED: No data ({elapsed:.2f}s)")
        
        # 3. Test Broker Summary
        print("\n" + "=" * 60)
        print("TEST 3: Broker Summary (BBCA, 2026-02-12)")
        t0 = time.time()
        bs = await client.get_broker_summary("BBCA", "2026-02-12")
        elapsed = time.time() - t0
        if bs:
            print(f"  OK: {len(bs.get('buy',[]))} buy, {len(bs.get('sell',[]))} sell ({elapsed:.2f}s)")
            if bs.get('buy'):
                print(f"  Top buy: {bs['buy'][0]}")
            if bs.get('sell'):
                print(f"  Top sell: {bs['sell'][0]}")
        else:
            print(f"  FAILED: No data ({elapsed:.2f}s)")
        
        # 4. Test Inventory
        print("\n" + "=" * 60)
        print("TEST 4: Inventory (BBCA)")
        t0 = time.time()
        inv = await client.get_inventory("BBCA")
        elapsed = time.time() - t0
        if inv:
            brokers = inv.get('brokers', [])
            print(f"  OK: {len(brokers)} brokers, dates={inv.get('firstDate')}->{inv.get('lastDate')} ({elapsed:.2f}s)")
            price_series = inv.get('priceSeries', [])
            print(f"  Price series: {len(price_series)} points")
            if brokers:
                b = brokers[0]
                print(f"  Sample broker: {b['code']} finalNetLot={b['finalNetLot']} pts={b['dataPoints']}")
        else:
            print(f"  FAILED: No data ({elapsed:.2f}s)")
        
        # 5. Test Transaction Chart
        print("\n" + "=" * 60)
        print("TEST 5: Transaction Chart (BBCA)")
        t0 = time.time()
        txn = await client.get_transaction_chart("BBCA")
        elapsed = time.time() - t0
        if txn:
            cum = txn.get('cumulative', {})
            daily = txn.get('daily', {})
            print(f"  OK: {len(cum)} cumulative, {len(daily)} daily ({elapsed:.2f}s)")
            print(f"  Cumulative methods: {list(cum.keys())}")
            if cum.get('market_maker'):
                mm = cum['market_maker']
                print(f"  MM latest={mm['latest']}, start={mm['start']}")
        else:
            print(f"  FAILED: No data ({elapsed:.2f}s)")
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETE")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_all())
