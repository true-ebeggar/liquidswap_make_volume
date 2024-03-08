import concurrent
import os
import random
import time
import traceback

from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base

from config import (SHUFFLE_ACCOUNTS, TOKEN_MAP, REFUEL_THRESHOLD,
                    MIN_AMOUNT_WITHDRAW, MAX_AMOUNT_WITHDRAW, MAX_THREAD,
                    AMOUNT_TO_LEFT_ON_ACC, SLEEP_FOR_THREAD_MIN, SLEEP_FOR_THREAD_MAX,
                    SLEEP_MIN, SLEEP_MAX, TOKEN_HOLD_TIME_MIN, TOKEN_HOLD_TIME_MAX, CHECK_TOKENS_BEFORE_WITHDRAW)
from data.database_actions import initialize_database
from transaction_staff import AptosTxnManager
from loguru import logger
from withdraw_okx import okx_withdraw


if os.path.exists('accounts.db'):
    pass
else:
    initialize_database('accounts.db')
Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'
    account_number = Column(Integer, primary_key=True)
    private_key = Column(String)
    address_to_withdraw = Column(String)
    target_volume = Column(Float)

engine = create_engine('sqlite:///accounts.db')
Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine)

def fetch_account_balance(account):
    txn_manager = AptosTxnManager(account.private_key)
    return account, txn_manager.get_account_balance()

def fetch_sorted_accounts_by_balance(session, num_threads=10):
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        accounts = session.query(Account).all()
        futures = [executor.submit(fetch_account_balance, account) for account in accounts]
        accounts_with_balances = [future.result() for future in futures]
    return [acc for acc, _ in sorted(accounts_with_balances, key=lambda x: x[1], reverse=True)]

def process_account(account_number, logger):
    with DBSession() as session:
        account = session.query(Account).filter_by(account_number=account_number).first()
        if not account:
            logger.error(f"Account_number: {account_number} not found. Exiting process.")
            return

        txn_manager = AptosTxnManager(account.private_key)
        balance_before = txn_manager.get_account_balance()
        readable_balance = balance_before / 10 ** 8
        logger.info(f"Initial balance for account {account_number}: {readable_balance}")

        if readable_balance < REFUEL_THRESHOLD:
            amount = round(random.uniform(MIN_AMOUNT_WITHDRAW, MAX_AMOUNT_WITHDRAW), 4)
            logger.info(f"Balance below threshold. Refueling account {account_number} with {amount} APT")
            if not okx_withdraw(str(txn_manager.address), amount, logger):
                return

            timeout, check_interval, start_time = 10 * 60, 30, time.time()
            while time.time() - start_time < timeout:
                current_balance = txn_manager.get_account_balance()
                if current_balance > balance_before:
                    logger.info(f"Account {account_number} refueled. New balance: {current_balance / 10 ** 8}")
                    break
                logger.info(f"Waiting for funds to arrive for account {account_number}...")
                time.sleep(check_interval)
            else:
                logger.error(f"Funds did not arrive within the 10-min period for account {account_number}.")
                return

        while account.target_volume > 0:
            try:
                balic = txn_manager.get_account_balance()
                random_token_key = random.choice(list(TOKEN_MAP.keys()))
                swap_amount = int(balic * round(random.uniform(0.93, 0.96), 3))
                swapped_amount_usd = txn_manager.swap_apt_to_token(random_token_key, swap_amount)
                account.target_volume -= swapped_amount_usd
                ss = random.randint(TOKEN_HOLD_TIME_MIN, TOKEN_HOLD_TIME_MAX)
                logger.info(f"Account {account_number} going to sleep for {ss}-sec before swap back")
                time.sleep(ss)
                swapped_back_amount_usd = txn_manager.swap_back(random_token_key)
                account.target_volume -= swapped_back_amount_usd
                session.commit()

                if account.target_volume <= 0:
                    logger.info(f"Account Number: {account.account_number} has reached the target volume. "
                                f"Transferring funds back to address: {account.address_to_withdraw}")

                    if CHECK_TOKENS_BEFORE_WITHDRAW is True:
                        logger.info('Checking map balance before withdraw')
                        for token_key in TOKEN_MAP.keys():
                            token_info = TOKEN_MAP[token_key]
                            resource = token_info['resource']
                            token_balance = txn_manager._get_coin_value(resource)
                            if token_balance and int(token_balance) > 0:
                                txn_manager.swap_back(token_key)
                                logger.info(
                                    f"Account {account_number} swapped back {token_key} to apt")

                    balance = txn_manager.get_account_balance()
                    random_factor = round(random.uniform(1.03, 1.11), 4)
                    amount_to_left = int((AMOUNT_TO_LEFT_ON_ACC * random_factor) * 10 ** 8)
                    amount_to_transfer = balance - amount_to_left
                    txn_manager.transfer(account.address_to_withdraw, amount_to_transfer)
                    session.delete(account)
                    session.commit()
                    break
                sheep = random.randint(SLEEP_MIN, SLEEP_MAX)
                logger.info(f"Account {account.account_number} going to sleep for {sheep}-sec before continue")
                time.sleep(sheep)
            except Exception as e:
                logger.critical(f"Error while swapping: {str(e)}")
                logger.critical(f"Error occurred in account {account_number} with token {random_token_key}")
                logger.critical(f"Traceback: {traceback.format_exc()}")
                break


def main():
    with DBSession() as session:
        accounts = session.query(Account).all()
        accounts = random.sample(accounts, len(accounts)) if SHUFFLE_ACCOUNTS else fetch_sorted_accounts_by_balance(session)

    with ThreadPoolExecutor(max_workers=MAX_THREAD) as executor:
        futures = []
        for account in accounts:
            future = executor.submit(process_account, account.account_number, logger)
            futures.append(future)

            s = random.randint(SLEEP_FOR_THREAD_MIN, SLEEP_FOR_THREAD_MAX)
            logger.info(f'Waiting for {s} seconds before starting the next thread.')
            time.sleep(s)

            if len(futures) >= MAX_THREAD:
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                futures = [f for f in futures if f not in done]

    for future in as_completed(futures):
        future.result()

if __name__ == "__main__":
    main()
