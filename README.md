

## Liquid Swap Automation

This project is designed to assist users in achieving their target volume on liquidswap.

### How It Works

The script operates by requiring users to input their withdrawal address and private key into two separate text files (`address_to_withdraw.txt` and `private_key.txt`). These inputs are crucial for the transaction process and withdrawing funds to a central exchange address after swap completion.

### Key Components:
- **Private Key**: Used for making transactions. Users must input this into `private_key.txt`.
- **Address to Withdraw**: Represents the central exchange address for withdrawing funds after swapping. This must be input into `address_to_withdraw.txt`.

### Configuration

Before running the script, users must configure their settings in `config.py`. This includes filling out the OKX api-key, api-secret, passphrase. File contains comments to guide you through the settings

### Important Notes:
- The script is semi-asynchronous, meaning it does support threading only. Users can specify the number of threads needed.
