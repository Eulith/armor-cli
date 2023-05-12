This repository holds a command-line interface to Eulith's DeFi Armor product.

# Using the CLI
## Set-up
As a one-time set-up step, run the set-up script:

```shell
./setup.sh
source .venv/bin/activate
```

This will create a virtual environment and install dependencies. Alternatively, you can directly
install dependencies from the `requirements.txt` file.

## Environment variables
Set the refresh token for the Eulith API:

```shell
export EULITH_REFRESH_TOKEN=<...>
```

If using a Ledger:

```shell
export EULITH_WALLET_TYPE=ledger
```

If using KMS:

```shell
export EULITH_WALLET_TYPE=kms
export AWS_CREDENTIALS_PROFILE_NAME=<...>
export EULITH_KMS_KEY=<...>  # the name of your key in KMS
```

## Addresses
Several Ethereum addresses are involved in setting up DeFi Armor and it's important to keep track of
the differences between them.

The **authorized trading address** is the wallet that will be used for trading once DeFi Armor is
enabled. We strongly encourage you to use a systematic signer (i.e., a signer that can sign without
human intervention) like KMS for your authorized trading address.

The **deployer address** is the wallet used in some of the steps below to deploy the Armor contract.
Currently the deployer address must be the same as the authorized trading address, but that
restriction will be lifted in the future.

The **Safe owner addresses** are the wallets that are owners of the Gnosis Safe on which the Armor
contract is a module. A recommended set-up is 5 owners (Ledger, Ledger, Ledger, KMS, KMS) with a
threshold of 3 and the KMS wallets being different than the authorized trading address. Note the Python client
supports Fireblocks raw signing so your owners could be (Fireblocks, Fireblocks, Ledger, KMS, KMS), for example.

Each command below is annotated with the wallet that should be used to run the command. See the
section above for how to configure different wallets via environment variables.

## Activating an Armor contract
First, deploy the Armor contract to the chain. This also deploys a new Gnosis Safe.

**WARNING:** On Ethereum mainnet, this transaction may be costly (0.3 ETH or more) depending on gas
prices.

```shell
# WALLET: deployer
python armor.py deploy-armor
```

Next, sign the Armor contract with a threshold of owners of your new Safe. For instance, to set up a
Safe with 3 owners and a threshold of 2, run this command twice.

```shell
# WALLET: Safe owner
python armor.py sign-armor-as-owner --auth-address XYZ
```

Enable the Armor contract as a module on the Safe, using the owner addresses from the previous step.

```shell
# WALLET: deployer
python armor.py enable-armor --threshold X --owner-addresses A B C
```

Next, create a draft client whitelist for trusted addresses.

```shell
# WALLET: deployer
python armor.py create-whitelist --addresses A B C
```

Repeat the signing process with a threshold of owners of the Safe to enable the whitelist.

```shell
# WALLET: Safe owner
python armor.py sign-whitelist --list-id XYZ
```

Your DeFi Armor contract is now ready to use! The DeFi Armor security policy will be applied to any
atomic transactions submitted through the regular Eulith API flow.

For example, using KMS:

```python
import boto3
from eulith_web3.eulith_web3 import EulithWeb3
from eulith_web3.kms import KmsSigner

aws_session = boto3.Session(profile_name="default")
aws_client = aws_session.client("kms")
wallet = KmsSigner(client, "alias/MY_KMS_KEY")

ew3 = EulithWeb3(
    eulith_url=EULITH_URL,
    eulith_refresh_token=EULITH_REFRESH_TOKEN,
    signing_middle_ware=construct_signing_middleware(wallet),
)

armor_address, safe_address = ew3.v0.get_armor_and_safe_addresses(wallet.address)
ew3.v0.start_atomic_transaction(wallet.address, safe_address)

ew3.eth.send_transaction(...)
ew3.eth.send_transaction(...)
ew3.eth.send_transaction(...)

ew3.v0.commit_atomic_transaction()
```

The DeFi Armor policy is applied when the atomic transaction is committed.

## Utility commands
View the addresses of the deployed Armor and Safe:

```shell
python armor.py addresses
```

View the current client whitelist:

```shell
python armor.py get-whitelist
```

View the current draft client whitelist:

```shell
python armor.py get-whitelist --draft
```

# Troubleshooting
## Ledger connection issues
If the command hangs on `Connecting to Ledger` for more than a second or two, kill the command with
Ctrl+C and re-run it again.

If the issue recurs, try plugging the Ledger into a different port of your machine.

## Failed with "we can't execute this request"
This error happens often on Arbitrum because of limited providers. Retry the request.
