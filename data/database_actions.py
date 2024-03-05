import sqlite3
import random
from liquidswap_make_volume.config import MIN_VOLUME, MAX_VOLUME

private_keys_file = 'data/private_keys.txt'
addresses_file = 'data/addresses_to_withdraw.txt'

def initialize_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
    if not cursor.fetchone():
        cursor.execute('''CREATE TABLE accounts
                          (account_number INTEGER PRIMARY KEY,
                           private_key TEXT,
                           address_to_withdraw TEXT,
                           target_volume REAL)''')

    with open(private_keys_file, 'r') as pk_file, open(addresses_file, 'r') as addr_file:
        private_keys = pk_file.readlines()
        addresses = addr_file.readlines()

    if len(private_keys) != len(addresses):
        raise ValueError("Mismatch in the number of private keys and addresses")

    for i, (private_key, address) in enumerate(zip(private_keys, addresses), start=1):
        target_volume = round(random.uniform(MIN_VOLUME, MAX_VOLUME), 4)
        cursor.execute("INSERT INTO accounts (account_number, private_key, address_to_withdraw, target_volume) VALUES (?, ?, ?, ?)",
                       (i, private_key.strip(), address.strip(), target_volume))

    conn.commit()
    conn.close()

