import models
import backend


def main(event):

    assets = backend.get_assets()
    model = models.FundamentalsRebalancingStakingHODL(
        assets, backend.get_sheet_by_name("model_inputs"), event['market_data'])
    instructions = model.instruct(
    )
    if instructions:
        print('lambda_func.py - main() - trade condition detected')
        for trade in instructions:

            backend.place_order(trade)
    else:
        print("no trade conditon - finished executing")


if __name__ == "__main__":
    main()


def lambda_handler(context, event):
    print(f"lambda_func.py invoked | context {context} | executing")
    main(event)
