import models
import backend
import mail_backend
from datetime import datetime
from datetime import timedelta


def main(context, market_data):
    timestamp = datetime.now()
    try:
        timestamp += timedelta(hours=context['timeoffset'])
    except(KeyError) as e:
        pass
    timestamp = timestamp.strftime("%m/%d/%Y, %H:%M:%S")
    assets = backend.get_assets()
    model = models.FundamentalsRebalancingStakingHODL(
        assets, backend.get_sheet_by_name("model_inputs"), market_data)
    instructions = model.instruct()
    prev_instructions = backend.get_sheet_by_name(
        "invoke_log").iloc[0]['instructions']
    backend.write_to_sheet(
        "invoke_log", [timestamp, context['source'], str(instructions)])
    if instructions:
        print('lambda_func.py - main() - trade condition detected')
        # only send mail if we didnt last time
        if prev_instructions == "FALSE":
            mail_backend.send_mail("trade alert", instructions)
        for trade in instructions:
            backend.place_order(trade)
    else:
        print("no trade conditon - finished executing")


if __name__ == "__main__":
    main()


def lambda_handler(context, event):
    '''
    :param context: {'source': string} optional: timeoffset
    :param event: backend.cmc_market_data()
    '''
    print(f"lambda_func.py invoked | context: {context}")
    main(context, event)
