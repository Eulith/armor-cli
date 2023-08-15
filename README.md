This repository holds a command-line interface to setup and transact using Eulith's DeFi Armor product. You can look under the hood of the CLI in this repo.

# DeFi Armor CLI Set-up
There are 3 steps to setting up the DeFi Armor product explained in this guide. These are:
* Step 1: Setting the parameters for the your deployment of the product.
* Step 2: Understanding the relvant address roles and deploying the full product.
* Step 3: Creating and approving the whitelist policy addresses.

Once you're finished with the setup, you'll be able to trade protected by DeFi Armor.

## Set-up Step 1

### Step 1.1: Install dependencies and create virtual environment
As a one-time set-up step, run the set-up script:

```shell
./setup.sh
source .venv/bin/activate
```

This will create a virtual environment and install dependencies. Alternatively, you can directly
install dependencies from the `requirements.txt` file.

### Step 1.2: Set environment variables (depends on wallet type)
If you are using Ledger, Trezor, KMS, or a custodian like Fireblocks, you will set the environment variables below.

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

If you are using a plan text private key (obviously for demo purposes), you will ignore the above and set the following environment variables.
```shell
EULITH_REFRESH_TOKEN=<...>
EULITH_NETWORK_TYPE=dev
EULITH_WALLET_TYPE=text
PRIVATE_KEY=<plain text private key goes here>
```

## Set-up Step 2

### Step 2.1: Understand DeFi Armor address roles
Several Ethereum addresses are involved in setting up DeFi Armor and it's important to keep track of
the differences between them.

The **authorized trading address** is the wallet that will be used for trading once DeFi Armor is
enabled. We strongly encourage you to use an automated signer (i.e., a signer that can sign without
human intervention) like (AWS/GCP) KMS for your authorized trading address.

The **deployer address** is the wallet used in some of the steps below to deploy the Armor contract.
Currently the deployer address must be the same as the authorized trading address, but that
restriction will be lifted in the future.

The **Safe owner addresses** are the addresses that own the account - the account being a Gnosis Safe contract. The critical role of these addresses is that they can withdraw the funds from the account given m of n signatures. A recommended set-up is 5 owners (Ledger, Ledger, Ledger, KMS, KMS) with a
threshold of 3 and the KMS wallets being different than the authorized trading address. Note the Python client
supports Fireblocks raw signing so your owners could be (Fireblocks, Fireblocks, Ledger, KMS, KMS), for example.

Each command below is annotated with the wallet that should be used to run the command. See the
section above for how to configure different wallets via environment variables.

### Step 2.2: Deploy the DeFi Armor product
First, deploy the on-chain component of DeFi Armor (we'll call this component "the Armor contract"). This step also deploys a new Gnosis Safe, which will hold your funds as your "account".

**WARNING:** On Ethereum mainnet, this transaction may be costly (0.3 ETH or more) depending on gas
prices.

```shell
# WALLET: deployer
./run.sh deploy-armor
```

### Step 2.3: Sign the Armor contract with enough owner addresses to meet the threshold of your new account. 

For instance, to set up an account that requires a threshold of 2 owner signatures, you will do the below twice.

Check your environment variables from Step 1.2 to make sure you are using the right wallet. If you are using the correct wallet, run:
```shell
# WALLET: Safe ew3
./run.sh sign-armor-as-ew3
```

For the next signature (for example, if you have run the above once but have a threshold of 2), change the environment variables to the new wallet. Then repeat this step.

You're finished with this step once you've run the above command with the threshold number of addresses for your account.

### Step 2.4: Active the Armor product

Run the following command, appending the addresses of _all_ account owners. _All_ meaning not only the signatures used above, but all owners associated with the account.

```shell
# WALLET: deployer
./run.sh enable-armor --threshold X --ew3-addresses 0x001 0x002 0x003
```

## Set-up Step 3

### Step 3.1: Create your first whitelist.
Create a draft client whitelist for trusted addresses. The addresses appended to the end of the command are the addresses in which you're comfortable with your funds being moved to.

```shell
# WALLET: deployer
./run.sh create-whitelist --addresses 0x001 0x002 0x003
```

### Step 3.2: Approve the whitelist with the owners of the account.
Repeat the signing process with a threshold of owners of the Safe to enable the whitelist. This means, similar to *Step 2.3*, you need to change the environment variables, run this script, than change and re-run for another owner until you've met the threshold number.

```shell
# WALLET: Safe ew3
./run.sh sign-whitelist --list-id XYZ
```

## Congrats! ##

Your DeFi Armor is now ready to use! The DeFi Armor security policy will be applied to any
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

## Intrinsic gas too low
(you need to add more gas to the tx with --gas... you'd be shocked how much gas Arbitrum will require, for example)

## Insufficient funds
(you don't have enough ETH in your wallet to cover the cost of the proposed transaction)

## Connection aborted
(Arbitrum sequencer told you to go fuck yourself, just try again)
