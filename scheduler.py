
import time
import lambda_func
from backend import cmc_market_data
import argparse
from tqdm import tqdm
from platform import platform

parser = argparse.ArgumentParser()
parser.add_argument(
    '-i', "--interval",
    help='wait time between invokes in minutes, default 30 minutes', type=int)
parser.add_argument("-t", "--timeoffset",
                    help='hours to offset time by', type=int)


args = parser.parse_args()
INTERVAL = args.interval*60 if args.interval else 30*60

context = {'source': f'scheduler: {platform()}'}
if args.timeoffset:
    context['timeoffset'] = args.timeoffset


while True:
    startup_string = f'starting scheduled run | interval: {int(INTERVAL/60)} min'
    if args.timeoffset:
        startup_string += f" | time_offset: {args.timeoffset}"
    print(startup_string)
    print("getting fresh market data...")
    market_data = cmc_market_data()
    print("invoking...")
    lambda_func.lambda_handler(
        context, market_data)
    for i in tqdm(range(INTERVAL), desc="[Ctrl+C to quit] - waiting"):
        time.sleep(1)
    print('scheduled run complete...')
