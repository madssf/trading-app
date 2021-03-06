from googleapiclient.errors import HttpError
import models
import backend
import mail_backend
from datetime import datetime
import pytz


def main(context, market_data):
    timestamp = datetime.now(pytz.timezone(
        "Europe/Berlin")).strftime("%m/%d/%Y, %H:%M:%S")
    instructions = None
    try:
        assets = backend.get_assets()
        model = models.McapModel(
            assets, backend.get_sheet_by_name("model_inputs"), market_data)
        instructions = model.instruct()

        symbols = list(assets.keys())
        tokens = []
        for element in symbols:
            tokens.append(assets[element]['tot'])

        # writing to db (g sheets)
        prev_assets = backend.get_sheet_by_name("assets_log").iloc[0]
        prev_symbols = prev_assets['symbols']
        prev_tokens = prev_assets['tokens']
        if prev_symbols != str(symbols) and prev_tokens != str(tokens):
            backend.write_to_sheet(
                "assets_log", [str(symbols), str(tokens), timestamp])
        prev_instructions = backend.get_sheet_by_name(
            "invoke_log").iloc[0]['instructions']
        backend.write_to_sheet(
            "invoke_log", [timestamp, context['source'], str(instructions)])
        total_mcap = 0
        for item in market_data:
            total_mcap += int(item['quote']['USD']['market_cap'])

        backend.write_to_sheet("mcap_log", [timestamp, total_mcap])
        # checking for instructions and initating trading
        if instructions:
            print('lambda_func.py - main() - trade condition detected')
            # only send mail if we get a fresh trade condition

            if prev_instructions == "FALSE":
                mail_backend.send_mail(instructions)
            '''   
            for trade in instructions:
                backend.place_order(trade)
            '''
        else:
            print("no trade conditon - finished executing")

    except (HttpError) as e:
        backend.write_to_sheet(
            "invoke_log", [timestamp, context['source'], str(e)])
        print(f"Error: {e}")


if __name__ == "__main__":
    main({'source': 'main function - cmd line'}, backend.cmc_market_data())


def lambda_handler(context, event):
    '''
    :param context: {'source': string} optional: timeoffset
    :param event: backend.cmc_market_data()
    '''
    print(f"lambda_func.py invoked | context: {context}")

    main(context, event)
