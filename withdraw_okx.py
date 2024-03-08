import random
import time
import ccxt

from config import (API_KEY,
                    API_SECRET,
                    PASSPHRASE)

import ccxt
import time

TOKEN = 'APT'
NETWORK = 'Aptos'


def okx_withdraw(address, amount_to_withdraw, logger):
    exchange = ccxt.okx({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'password': PASSPHRASE,
        'enableRateLimit': True,
    })

    max_retries = 20
    retry_delay = 2
    chain_name = f"{TOKEN}-{NETWORK}"

    for attempt in range(1, max_retries + 1):
        try:
            withdraw_params = {
                "toAddress": address,
                "chainName": chain_name,
                "dest": 4,
                "fee": 0.001,
                "pwd": '-',
                "amt": amount_to_withdraw,
                "network": NETWORK
            }

            exchange.withdraw(TOKEN, amount_to_withdraw, address, params=withdraw_params)
            logger.success(f'Transferred {amount_to_withdraw} {TOKEN} to {address}')
            return True

        except Exception as error:
            logger.error(f'Attempt {attempt}: Failed to transfer {amount_to_withdraw} {TOKEN}: {error}')

            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error(f"All attempts failed after {max_retries} retries.")
                return False