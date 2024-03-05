import random
import time
import ccxt

from config import (API_KEY,
                    API_SECRET,
                    PASSPHRASE)

TOKEN = 'APT'
NETWORK = 'Aptos'
def get_withdrawal_fee(symbolWithdraw, chainName):
    exchange = ccxt.okx({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'password': PASSPHRASE,
        'enableRateLimit': True,
    })
    currencies = exchange.fetch_currencies()
    for currency in currencies:
        if currency == symbolWithdraw:
            currency_info = currencies[currency]
            network_info = currency_info.get('networks', None)
            if network_info:
                for network in network_info:
                    network_data = network_info[network]
                    network_id = network_data['id']
                    if network_id == chainName:
                        withdrawal_fee = currency_info['networks'][network]['fee']
                        if withdrawal_fee == 0:
                            return 0
                        else:
                            return withdrawal_fee
    raise ValueError(f"Fail")

def okx_withdraw(address, amount_to_withdrawal, logger):
    exchange = ccxt.okx({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'password': PASSPHRASE,
        'enableRateLimit': True,
    })
    max_retries = 20
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            chainName = TOKEN + "-" + NETWORK
            fee = get_withdrawal_fee(TOKEN, chainName)
            exchange.withdraw(TOKEN, amount_to_withdrawal, address,
                params={
                    "toAddress": address,
                    "chainName": chainName,
                    "dest": 4,
                    "fee": fee,
                    "pwd": '-',
                    "amt": amount_to_withdrawal,
                    "network": NETWORK
                }
            )

            logger.info(f'Transferred {amount_to_withdrawal} {TOKEN} to {address}')
            return True
        except Exception as error:
            logger.error(f'Attempt {attempt + 1}: Failed to transfer {amount_to_withdrawal} {TOKEN}: {error}')
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"All attempts failed after {max_retries} retries.")
                return False

