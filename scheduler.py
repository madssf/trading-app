
import time
import lambda_func
from tqdm import tqdm
from backend import cmc_market_data

INTERVAL = 30*60

scheduler_string = "scheduler active - [Ctrl+C to quit]"

while True:
    print(scheduler_string)
    print('getting fresh market data...')
    market_data = cmc_market_data()
    print("invoking...")
    lambda_func.lambda_handler({'source': 'scheduler.py'}, market_data)
    for i in tqdm(range(INTERVAL), desc="waiting for next invoke"):
        time.sleep(1)
    print('---------')
