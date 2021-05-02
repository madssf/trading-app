import json
import pygsheets
from google.oauth2 import service_account


def get_sheet_by_name(name):
    with open('sheets_config.json') as source:
        info = json.load(source)

    credentials = service_account.Credentials.from_service_account_info(info)

    client = pygsheets.authorize(service_account_file='sheets_config.json')

    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1ckQ3JaGAsowqNDCp_DrqQxqfvpPrFvY3TpYrtewrwEE/edit?usp=sharing"
    sheet_data = client.sheet.get(
        '1ckQ3JaGAsowqNDCp_DrqQxqfvpPrFvY3TpYrtewrwEE')

    sheet = client.open_by_key('1ckQ3JaGAsowqNDCp_DrqQxqfvpPrFvY3TpYrtewrwEE')
    return sheet.worksheet_by_title(name).get_as_df()


def get_sheets(names):
    return {name: get_sheet_by_name(name) for name in names}

# combines all assets from everywhere for total value (incl. locked staking)


def get_assets():
    return
