import json
import random
import time
import requests
from aptos_sdk.account import Account
from aptos_sdk.client import RestClient
from pyuseragents import random as random_ua
from loguru import logger
from config import MAX_SLIPPAGE_PERCENT, TOKEN_MAP, NODE
from aptos_sdk.client import ClientConfig


ClientConfig.max_gas_amount = 100_00
SLIPPAGE = (100 - MAX_SLIPPAGE_PERCENT) / 100
Z8 = 10**8
Z6 = 10**6


class AptosTxnManager:
    def __init__(self, key):
        self.account = Account.load_key(key)
        self.address = self.account.address()
        self.logger = logger
        self.rest_client = RestClient(NODE)

    def transfer(self, recipient, amount: int):
        payload = {
            "type": "entry_function_payload",
            "function": "0x1::aptos_account::transfer_coins",
            "type_arguments": ["0x1::aptos_coin::AptosCoin"],
            "arguments": [
                str(recipient),
                str(amount),
            ],
        }
        self._submit_and_log_transaction(payload)

    def _submit_and_log_transaction(self, payload):
        try:
            txn = self.rest_client.submit_transaction(self.account, payload)
            self.rest_client.wait_for_transaction(txn)
            self.logger.info(f'Success: https://explorer.aptoslabs.com/txn/{txn}?network=mainnet')
        except AssertionError as e:
            self.logger.error(f"AssertionError: {e}")
        except Exception as e:
            self.logger.critical(f"An unexpected error occurred: {e}")

    def _register_coin(self, to_register: str):
        payload = {
            "type": "entry_function_payload",
            "function": "0x1::managed_coin::register",
            "type_arguments": [
                to_register
            ],
            "arguments": []
        }
        self._submit_and_log_transaction(payload)

    def _check_registration(self, to_check: str):
        try:
            coin_type = f"0x1::coin::CoinStore<{to_check}>"
            url = f"https://fullnode.mainnet.aptoslabs.com/v1/accounts/{self.address}/resources?limit=9999"
            response = requests.get(url)
            # print(json.dumps(response.json(), indent=4))
            return any(item.get('type', '') == coin_type for item in response.json())
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            return False

    def _get_coin_value(self, coin_to_check: str):
        try:
            coin_store_type = f"0x1::coin::CoinStore<{coin_to_check}>"
            url = f"https://fullnode.mainnet.aptoslabs.com/v1/accounts/{self.address}/resources?limit=9999"
            response = requests.get(url)
            # print(json.dumps(response.json(), indent=4))

            for item in response.json():
                if item.get('type', '') == coin_store_type:
                    coin_data = item.get('data', {}).get('coin', {})
                    coin_value = coin_data.get('value')
                    return coin_value

            return None
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            return None

    def register_all_map(self):
        for token, resource in TOKEN_MAP.items():
            self.logger.info(f"Checking registration for {token.upper()}...")
            register = self._check_registration(to_check=resource)
            if register is False:
                self.logger.info(f"{token.upper()} is not register, fixing it now...")
                self._register_coin(to_register=resource)
                s = random.randint(20, 45)
                self.logger.info(f"Going to sleep for {s} sec before next token")
                time.sleep(s)
                continue
            elif register is True:
                self.logger.info(f"{token.upper()} is already register, skipping it...")
        self.logger.info("All tokens checked, processing to swaps")

    def get_account_balance(self):
        max_retries = 3
        retries = 0

        while retries < max_retries:
            try:
                return int(self.rest_client.account_balance(account_address=self.address))
            except Exception as e:
                if "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>" in str(e):
                    self.logger.critical("Account does not exist")
                    return False
                else:
                    retries += 1
                    self.logger.error(f"Error occurred: {e} "
                                      f"\nRetry {retries}/{max_retries}")

        self.logger.critical("Maximum retries reached. Unable to get account balance.")
        return None

    def get_token_price(self, token_to_get):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "If-None-Match": 'W/"927-wrpuzNZ1tVuG1LAZ/4/YRXvNyfY"',
            "Origin": "https://liquidswap.com",
            "Referer": "https://liquidswap.com/",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Opera";v="107", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": random_ua()
        }
        attempts = 0
        while attempts < 10:
            try:
                response = requests.get(
                    'https://control.pontem.network/api/integrations/fiat-prices?currencies=apt,usdc,usdt,doodoo',
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    # print(json.dumps(data, indent=4))
                    for token in data:
                        if token['coinType'].lower() == token_to_get.lower():
                            return token['price']
                    return None
                else:
                    pass
            except Exception:
                pass
            finally:
                attempts += 1
                time.sleep(1)

        self.logger.error("Unable to fetch price after 10 retries. Giving up...")
        return None

    def swap_apt_to_token(self, token, resource, amount_apt_wei: int):
        apt_price = self.get_token_price('apt')
        aptos_float = amount_apt_wei / Z8
        token_price = self.get_token_price(token)
        apt_amount_usd = apt_price * aptos_float
        token_amount_ideal = apt_amount_usd / token_price
        token_amount_slip = token_amount_ideal * SLIPPAGE

        if token == 'doodoo':
            token_amount_slip_wei = int(token_amount_slip * Z8)
            router = "0x163df34fccbf003ce219d3f1d9e70d140b60622cb9dd47599c25fb2f797ba6e::curves::Uncorrelated"
            function = '0x163df34fccbf003ce219d3f1d9e70d140b60622cb9dd47599c25fb2f797ba6e::scripts::swap'
        else:
            token_amount_slip_wei = int(token_amount_slip * Z6)
            router = "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::curves::Uncorrelated"
            function = "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::scripts_v2::swap"

        payload = {
            "type": "entry_function_payload",
            "function": function,
            "type_arguments": [
                "0x1::aptos_coin::AptosCoin",
                str(resource),
                router
            ],
            "arguments": [
                str(amount_apt_wei),
                str(token_amount_slip_wei)
            ],
        }
        self.logger.info(f"{self.address} swapping {aptos_float} APT to {token.upper()}")
        self._submit_and_log_transaction(payload)
        return round(apt_amount_usd, 2)


    def swap_back(self, token, resource):
        token_value = int(self._get_coin_value(resource))

        if token == 'doodoo':
            token_float = token_value / Z8
            router = "0x163df34fccbf003ce219d3f1d9e70d140b60622cb9dd47599c25fb2f797ba6e::curves::Uncorrelated"
            function = '0x163df34fccbf003ce219d3f1d9e70d140b60622cb9dd47599c25fb2f797ba6e::scripts::swap'
        else:
            token_float = token_value / Z6
            router = "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::curves::Uncorrelated"
            function = "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::scripts_v2::swap"

        price = self.get_token_price(token)
        usd_value = price * token_float
        apt_price = self.get_token_price('apt')
        apt_ideal = usd_value / apt_price
        apt_slip = apt_ideal * SLIPPAGE
        apt_slip_wei = int(apt_slip * Z8)

        payload = {
            "type": "entry_function_payload",
            "function": function,
            "type_arguments": [
                str(resource),
                "0x1::aptos_coin::AptosCoin",
                router
            ],
            "arguments": [
                str(token_value),
                str(apt_slip_wei)
            ],
        }

        self.logger.info(f"{self.address} swapping {token_float} {token.upper()} back to APT")
        self._submit_and_log_transaction(payload)
        return round(usd_value, 2)


if __name__ == "__main__":
    manager = AptosTxnManager('0x837bf1f5193b34feb9a83aabac78d64f5f7c5b9edeef081aa6685d87def77c34')
    # manager.register_all_map()
    for token, resource in TOKEN_MAP.items():
        balance = manager.get_account_balance()
        one_forth = int(balance * 0.25)
        print(manager.swap_apt_to_token(token, resource, one_forth))
        time.sleep(10)
        print(manager.swap_back(token, resource))
