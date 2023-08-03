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
The Armor CLI requires some environment variables to be set.

```shell
export EULITH_REFRESH_TOKEN=<...>
export EULITH_NETWORK_TYPE=mainnet  # choices: mainnet, arb, goerli
export EULITH_AUTH_ADDRESS=0x123  # the authorized trading address (see below)

# If using a Ledger:
export EULITH_WALLET_TYPE=ledger

# If using a Trezor:
export EULITH_WALLET_TYPE=trezor

# If using KMS:
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
./run.sh deploy-armor
```

Next, sign the Armor contract with a threshold of owners of your new Safe. For instance, to set up a
Safe with 3 owners and a threshold of 2, run this command twice.

```shell
# WALLET: Safe ew3
./run.sh sign-armor-as-ew3
```

Enable the Armor contract as a module on the Safe, using the owner addresses from the previous step.

```shell
# WALLET: deployer
./run.sh enable-armor --threshold X --ew3-addresses 0x001 0x002 0x003
```

Next, create a draft client whitelist for trusted addresses.

```shell
# WALLET: deployer
./run.sh create-whitelist --addresses 0x001 0x002 0x003
```

Repeat the signing process with a threshold of owners of the Safe to enable the whitelist.

```shell
# WALLET: Safe ew3
./run.sh sign-whitelist --list-id XYZ
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

## Armor Utility commands
View the addresses of the deployed Armor and Safe:

```shell
./run.sh addresses
```

View the current client whitelist:

```shell
./run.sh get-whitelist
```

View the current draft client whitelist:

```shell
./run.sh get-whitelist --draft
```

## Safe Utility Commands
Armor can't work without its Safe. We have some basic utility commands to do basic transfers in and out
of the safe with owner approval.

View the Safe's balance of a given token
```shell
./run.sh safe-balance --token 0x... --safe 0x...
```

Start a transfer from the safe to a `dest` address. This will print out a hash that you need
to approve with a threshold number of owners.
```shell
./run.sh start-safe-transfer --token 0x... --safe 0x... --dest 0x... --amount 0.1
```

Approve a Safe transaction hash with an owner. Note the owner that will be approving in this command is the
connected wallet configured by the above environment variables.
```shell
./run.sh safe-approve-hash --safe 0x... --hash 0x...
```

Once you have approved a given hash with a sufficient number of owners, you can execute the transaction.
Note that the owners passed here must line up with owners you approved the hash with.
```shell
./run.sh execute-safe-transfer --safe 0x... --token 0x... --dest 0x... --amount 0.1 --owners 0x... 0x... 
```

# Troubleshooting
## Ledger connection issues
If the command hangs on `Connecting to Ledger` for more than a second or two, kill the command with
Ctrl+C and re-run it again.

If the issue recurs, try plugging the Ledger into a different port of your machine.

## Failed with "we can't execute this request"
This error happens often on Arbitrum because of limited providers. Retry the request.
