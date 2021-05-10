
from json.decoder import JSONDecodeError
import time
import lambda_func
from backend import cmc_market_data, write_to_sheet
import argparse
from tqdm import tqdm
from platform import platform

parser = argparse.ArgumentParser()
parser.add_argument(
    '-i', "--interval",
    help='wait time between invokes in minutes, default 30 minutes', type=int)

args = parser.parse_args()
INTERVAL = args.interval*60 if args.interval else 30*60

context = {'source': f'scheduler: {platform()}'}

while True:
    startup_string = f'starting scheduled run | interval: {int(INTERVAL/60)} min'
    print(startup_string)
    print("getting fresh market data...")
    try:
        market_data = cmc_market_data()
        print("invoking...")
        lambda_func.lambda_handler(
            context, market_data)
    except (JSONDecodeError) as e:
        print(f'Error: {e}')

    for i in tqdm(range(INTERVAL), desc="[Ctrl+C to quit] - waiting"):
        time.sleep(1)
    print('scheduled run complete...')
