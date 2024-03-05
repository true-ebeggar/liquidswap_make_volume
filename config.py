# API Configuration for OKX
API_KEY = "your_api_key_here"  # Your unique API key provided by OKX for programmatic access to your account.
API_SECRET = "your_api_secret_here"  # The secret key associated with your API key. Keep this confidential.
PASSPHRASE = "your_passphrase_here"  # A passphrase you set up in the OKX API management for an additional layer of security.

# Withdrawal Settings
MIN_AMOUNT_WITHDRAW = 2  # The minimum amount to withdraw in a single transaction.
MAX_AMOUNT_WITHDRAW = 4  # The maximum amount to withdraw in a single transaction.

# Account Refueling Threshold
REFUEL_THRESHOLD = 1  # The account balance threshold at which an account is considered ready for refueling.

# Operational Behavior
SHUFFLE_ACCOUNTS = True  # Whether to randomize the order of accounts before processing (True/False).
MAX_THREAD = 1  # The maximum number of concurrent threads for processing.

# Thread Timing
SLEEP_FOR_THREAD_MIN = 15  # Minimum sleep duration (in seconds) between starting threads to avoid simultaneous launches.
SLEEP_FOR_THREAD_MAX = 35  # Maximum sleep duration (in seconds) between starting threads.

# Transaction Settings
MAX_SLIPPAGE_PERCENT = 1.5  # The maximum acceptable slippage percentage for transactions.
AMOUNT_TO_LEFT_ON_ACC = 0.1  # The amount of tokens to be left in the account after processing.

# Volume Targets
MIN_VOLUME = 700  # The minimum target volume that will be assigned to account.
MAX_VOLUME = 1200  # The maximum target volume that will be assigned to account.

# Token Management
TOKEN_HOLD_TIME_MIN = 69  # Minimum time (in seconds) to hold a token before considering a swap back.
TOKEN_HOLD_TIME_MAX = 100  # Maximum time (in seconds) to hold a token before considering a swap back.

# Operational Delays
SLEEP_MIN = 60  # Minimum sleep duration (in seconds) before moving on to the next token.
SLEEP_MAX = 180  # Maximum sleep duration (in seconds) before moving on to the next token.

# Token Mapping
TOKEN_MAP = {
    'usdc': '0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC',
    'usdt': '0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDT',
    'doodoo': '0x73eb84966be67e4697fc5ae75173ca6c35089e802650f75422ab49a8729704ec::coin::DooDoo'
}  # A dictionary mapping token symbols to their respective blockchain addresses.

# Network Node
NODE = "https://fullnode.mainnet.aptoslabs.com/v1"  # The URL of the blockchain node to connect to for transactions.
