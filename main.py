import concurrent
import os
import random
import time

from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base

from config import (SHUFFLE_ACCOUNTS, TOKEN_MAP, REFUEL_THRESHOLD,
                    MIN_AMOUNT_WITHDRAW, MAX_AMOUNT_WITHDRAW, MAX_THREAD,
                    AMOUNT_TO_LEFT_ON_ACC, SLEEP_FOR_THREAD_MIN, SLEEP_FOR_THREAD_MAX,
                    SLEEP_MIN, SLEEP_MAX, TOKEN_HOLD_TIME_MIN, TOKEN_HOLD_TIME_MAX)
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

def process_account(account_number, logger):
    with DBSession() as session:
        account = session.query(Account).filter_by(account_number=account_number).first()
        if not account:
            logger.error(f"Account_number: {account_number} not found. Exiting process.")
            return

        txn_manager = AptosTxnManager(account.private_key)
        balance_before = txn_manager.get_account_balance()
        readable_balance = balance_before / (10 ** 8)
        logger.info(f"Initial balance for account {account_number}: {readable_balance}")

        if readable_balance < REFUEL_THRESHOLD:
            amount = round(random.uniform(MIN_AMOUNT_WITHDRAW, MAX_AMOUNT_WITHDRAW), 4)
            logger.info(f"Balance below threshold. Refueling account {account_number} with {amount} APT")
            if not okx_withdraw(str(txn_manager.address), amount, logger):
                return

            timeout = 10 * 60
            check_interval = 30
            start_time = time.time()

            while time.time() - start_time < timeout:
                current_balance = txn_manager.get_account_balance()
                if current_balance > balance_before:
                    logger.info(f"Account {account_number} refueled. New balance: {current_balance / (10 ** 8)}")
                    break
                else:
                    logger.info(f"Waiting for funds to arrive for account {account_number}...")
                    time.sleep(check_interval)
            else:
                logger.error(f"Funds did not arrive within the 10-min period for account {account_number}.")
                return

        txn_manager.register_all_map()

        while account.target_volume > 0:
            balic = txn_manager.get_account_balance()
            token, resource = random.choice(list(TOKEN_MAP.items()))
            swap_amount = int(balic * round(random.uniform(0.93, 0.96), 3))
            swapped_amount_usd = txn_manager.swap_apt_to_token(token, resource, swap_amount)
            account.target_volume -= swapped_amount_usd
            ss = random.randint(TOKEN_HOLD_TIME_MIN, TOKEN_HOLD_TIME_MAX)
            logger.info(f"Account {account_number} going to sleep for {ss}-sec before swap back")
            time.sleep(ss)
            swapped_back_amount_usd = txn_manager.swap_back(token, resource)
            account.target_volume -= swapped_back_amount_usd
            session.commit()

            if account.target_volume <= 0:
                logger.info(f"Account Number: {account.account_number} has reduced target volume to zero."
                            f" Sending founds back to withdraw address {account.address_to_withdraw}")
                b = txn_manager.get_account_balance()
                c = round(random.uniform(1.03, 1.11), 4)
                b_to_left = (b - int((AMOUNT_TO_LEFT_ON_ACC * c) * 10**8))
                txn_manager.transfer(account.address_to_withdraw, b_to_left)

                session.delete(account)
                session.commit()
                break

            sheep = random.randint(SLEEP_MIN, SLEEP_MAX)
            logger.info(F"Account {account.account_number} going to sleep for {sheep}-sec before continue")
            time.sleep(sheep)


def main():
    session = DBSession()
    accounts = session.query(Account).all()
    if SHUFFLE_ACCOUNTS:
        random.shuffle(accounts)
    session.close()

    futures = []
    with ThreadPoolExecutor(max_workers=MAX_THREAD) as executor:
        for account in accounts:
            future = executor.submit(process_account, account.account_number, logger)
            futures.append(future)

            s = random.randint(SLEEP_FOR_THREAD_MIN, SLEEP_FOR_THREAD_MAX)
            logger.info(f'Waiting for {s} seconds before starting the next thread.')
            time.sleep(s)

            if len(futures) >= MAX_THREAD:
                done, _ = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
                futures = [f for f in futures if f not in done]

    for future in concurrent.futures.as_completed(futures):
        future.result()

if __name__ == "__main__":
    main()

