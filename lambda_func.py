import models
import backend
import mail_backend


def main(market_data):

    assets = backend.get_assets()
    model = models.FundamentalsRebalancingStakingHODL(
        assets, backend.get_sheet_by_name("model_inputs"), market_data)
    instructions = model.instruct()
    if instructions:
        print('lambda_func.py - main() - trade condition detected')
        mail_backend.send_mail("trade alert", instructions)
        for trade in instructions:
            backend.place_order(trade)
    else:
        print("no trade conditon - finished executing")


if __name__ == "__main__":
    main()


def lambda_handler(context, event):
    '''
    :param context: {'source': string}
    :param event: backend.cmc_market_data()
    '''
    print(f"lambda_func.py invoked | context: {context}")
    main(event)
