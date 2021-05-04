
import time
import lambda_func
from tqdm import tqdm
from backend import cmc_market_data

INTERVAL = 15*60


while True:
    print("--------")
    print('scheduler activated - getting fresh market data...')
    market_data = cmc_market_data()
    print("invoking...")
    lambda_func.lambda_handler({'source': 'scheduler.py'}, market_data)
    for i in tqdm(range(INTERVAL), desc="[Ctrl+C to quit] - waiting"):
        time.sleep(1)
    print('---------')
