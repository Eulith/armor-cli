# DeFi Armor 

If you want to do systematic trading (automatic signing, no human intervention for a given trade), you open yourself up to a world of risk.

People have different strategies to manage this risk. We think they all make serious tradeoffs in flexibility and security.

Ideally, you would have infrastructure for systematic trading that:

1. Allows you to generically interact with whatever protocol you want,

2. Without having to move your funds to some sort of "proxy trader,"

3. In a way that enforces security policies such as "don't let anyone transfer ERC20 tokens to an unknown destination"

This is what DeFi Armor does. We think it's the best on-chain systematic trading infrastructure in the market. It's secure, reliable, and protocol agnostic.

# Key Overview

| Address (Key/Account) | Who Controls?  | Privileges                 | Key Host        | ETH?      | Assets? | Raw Signing? | Compromised?                                                                                                             | Lost?                                                                               |
|-----------------------|----------------|----------------------------|-----------------|-----------|---------|--------------|--------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| Vault Owner           | Client         | Root with owner threshold  | Client's choice | ✅ (gas)   | ❌       | ❌            | Disable for vault and replace, no problem if other owner keys not compromised at the same time.                          | Disable & replace lost owner. No problem if other owners not lost at the same time. |
| Auto-Trading          | Client via ACE | Trading, subject to policy | AWS KMS         | ✅ (gas)   | ❌       | ✅            | Disable user, replace Armor module with new key. Auto-Trading key not useful outside of policy.                          | Replace Armor module, reconfigure ACE. No problem other than a little downtime.     |
| Manual-Trading        | Client         | Trading, subject to policy | Client's choice | ✅ (gas)   | ❌       | ❌            | Disable user, replace Armor module with new key. Manual-Trading key not useful outside of policy.                        | Replace Armor module, reconfigure ACE. No problem other than a little downtime.     |
| Instruction           | Client         | Instruct & authorize ACE   | Client's choice | ❌         | ❌       | ❌            | Re-key ACE (simple config change)                                                                                        | Re-key ACE (simple config change)                                                   |
| CoSigner              | Eulith         | Co-sign transactions       | AWS KMS         | ❌         | ❌       | ❌            | Non-extractable key allows us to regain control effectively; compromised cosigner not useful without compromised client. | Disable all on-chain modules, deploy new                                            |
| Vault                 | Blockchain     | N/A                        | Blockchain      | ✅ (asset) | ✅       | ❌            | Remove all assets                                                                                                        | N/A                                                                                 |
| Armor Module          | Blockchain     | N/A                        | Blockchain      | ❌         | ❌       | ❌            | Disable & replace module                                                                                                 | N/A                                                                                 |


# DeFi Armor Set-up via CLI
There are 3 steps to setting up the DeFi Armor product explained in this guide. These are:
* Step 1: Setting the parameters for the deployment of the product.
* Step 2: Understanding the relevant address roles and deploying the full product.
* Step 3: Creating and approving the whitelist policy addresses.

Once you're finished with the setup, you'll be able to trade protected by DeFi Armor. Will show you how to trade after the 3 Step setup.

Before getting started, we recommend scrolling down to the **Troubleshooting** section at the bottom to glance at the, hopefully unlikely, but possible errors you can get and what to do about them.

## Set-up Step 1

### Step 1.1: Install dependencies and create virtual environment
As a one-time set-up step, run the set-up script:

```shell
./setup.sh
```

This will create a virtual environment and install dependencies. Alternatively, you can directly
install dependencies from the `requirements.txt` file.

### Step 1.2: Set environment variables (depends on wallet type)
If you are using Ledger, Trezor, KMS, or a custodian like Fireblocks, you will set the environment variables in the .env file.

If you are using a plain text key for demo purposes, your `.env` file should look like this:
```shell
EULITH_REFRESH_TOKEN=<you get this from us>
EULITH_NETWORK_TYPE=<choices: mainnet, arb, goerli, poly, dev>
EULITH_TRADING_ADDRESS=<0x123, the auto or manual trading key address (see below)>

# If using a plain text private key (for demo obviously)
EULITH_WALLET_TYPE=text
PRIVATE_KEY=<plain text key goes here>
```

If you are using an AWS KMS wallet (which we recommend for production), your `.env` file should look like this:
```shell
EULITH_REFRESH_TOKEN=<you get this from us>
EULITH_NETWORK_TYPE=<choices: mainnet, arb, goerli, poly, dev>
EULITH_TRADING_ADDRESS=<0x123, the address of your trading key (see the table above if you're unsure)>

# If using KMS:
EULITH_WALLET_TYPE=kms
AWS_CREDENTIALS_PROFILE_NAME=<...>
EULITH_KMS_KEY=<...>  # the name of your key in KMS
```

## Set-up Step 2

### Step 2.1: Understand DeFi Armor address roles
Several Ethereum addresses are involved in setting up DeFi Armor and it's important to keep track of
the differences between them.

The **(auto or manual) trading key address** is the wallet that will be used for trading once DeFi Armor is
enabled. If you intend to do automated trading, you'll need to use an automated signer (i.e., a signer that can sign without
human intervention) like (AWS/GCP) KMS for your auto-trading key.

The **deployer address** is the wallet used in some steps below to deploy the Armor contract.
It doesn't matter what address this is, it just needs to have enough ETH to get the setup
transactions confirmed on-chain.

The **vault owner addresses** are the addresses that own the vault - the vault being a [Gnosis Safe](https://safe.global) contract. 
The critical role of these addresses is that they can withdraw the funds from the account given `m` of `n` signatures. 
A recommended set-up is 5 owners (Trezor, Trezor, Trezor, KMS, KMS) with a
threshold of 3 and the KMS wallets being different from the auto-trading key address. Note the Python client
supports Fireblocks raw signing so your owners could be (Fireblocks, Fireblocks, Ledger, KMS, KMS), for example.

Each command below is annotated with the wallet that should be used to run the command. See the
section above for how to configure different wallets via environment variables.

### Step 2.2: Deploy the DeFi Armor product
First, deploy the on-chain component of DeFi Armor (we'll call this component "the Armor contract"). 
This step also deploys a new Gnosis Safe, which will hold your funds as your "vault".

**WARNING:** On Ethereum mainnet, this transaction may be costly (0.3 ETH or more) depending on gas
prices.

```shell
# WALLET: deployer
./run.sh deploy-armor
```

### Step 2.3: Sign the Armor contract with enough owner addresses to meet the threshold of your new account. 

For instance, to set up an account that requires a threshold of 2 owner signatures, you will do the below twice,
changing the connected wallet to one of the owners each time.

Check your environment variables from Step 1.2 to make sure you are using the right wallet.
You can see the address of the connected wallet by running
```shell
./run.sh show-wallet
```

After verifying that you're using the correct wallet, run:
```shell
# WALLET: Owner <m>/<n>
./run.sh sign-armor-as-owner
```

For the next signature (for example, if you have run the above once but have a threshold of 2), 
change the environment variables to the new wallet. Then repeat this step.

You're finished with this step once you've run the above command with the threshold number of addresses for your account.

### Step 2.4: Active the Armor product

Run the following command, appending the addresses of _all_ account owners. _All_ meaning not only the signatures used above, 
but all owners associated with the account.

```shell
# WALLET: deployer
./run.sh enable-armor --threshold X --owner-addresses 0x001 0x002 0x003
```

## Set-up Step 3

### Step 3.1: Create your first whitelist.
Create a draft client whitelist for trusted addresses. The addresses appended to the end of the command are the addresses in which you're comfortable with your funds being moved to.

```shell
# WALLET: deployer
./run.sh create-whitelist --addresses 0x001 0x002 0x003
```

### Step 3.2: Approve the whitelist with the owners of the account.
Repeat the signing process with a threshold of owners of the Safe to enable the whitelist. 
This means, similar to *Step 2.3*, you need to change the environment variables, run this script, 
then change and re-run for another owner until you've met the threshold number.

```shell
# WALLET: Owner <m>/<n>
./run.sh sign-whitelist --list-id XYZ
```

# Congrats, you're set up!

## Let's test it with some trades.

Your DeFi Armor is now ready to use! The DeFi Armor security policy will be applied to any
transactions submitted through the regular Eulith API flow.

The following sections explain exactly how to create transactions to trade. This part is important, because there are some initially counter-intuitive requirements.

### Eulith Atomic Transactions: Why and How

In order to programmatically trade with DeFi Armor, you need to use one of our client libraries (in Python, Typescript, Java, or Rust). Our libraries are all wrappers around Web3; for example, anything you can do in web3.py works out of the box with our python client library. You cannot use web3 by itself - the reason is because there's a whole lot that goes on under the hood to make DeFi Armor possible, and that includes some additional client-side tools. The most important tool is the **atomic transaction**.

An **atomic transaction** is simply a transaction which has 1 or more internal transactions inside of it. These transactions get executed all or none, there's no partial execution. They're easy to do with our client.

In **python** it looks like:
```python
ew3.v0.start_atomic_transaction(wallet.address, safe_address)

# web3.py transaction 1
# web3.py transaction 2

atomic_tx = ew3.v0.commit_atomic_transaction()
tx = ew3.eth.send_transaction(atomic_tx)
receipt = ew3.eth.wait_for_transaction_receipt(tx)
```

In **typescript** it looks like:
```typescript
// Start Atomic Tx
const atomicTransaction = new Eulith.AtomicTx({
    web3: ew3,
    accountAddress: await acct.getAddress(),
});

// web3.js transaction 1
// web3.js transaction 2

// Commit Atomic Tx
const combinedTransactionAsTxParams = await atomicTransaction.commit();

// Sign and send
const txHash: string = await ew3.eulith_send_and_sign_transaction(
    combinedTransactionAsTxParams
);

// Get tx hash
const txReceipt: TransactionReceipt = await ew3.eth.getTransactionReceipt(
    txHash
);
```

That's everything you need to know about trading programmatically with DeFi Armor.

## Full Working Example
Let's give 2 full working examples, in python, using an AWS KMS key. The first will do 3 transfers. The second will take 3 transfers and executes them as 1 transaction.

## If the below is confusing, please call us and we will ship a feature to make doing non-atomic transactions much more convenient

#### First example
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
ew3.eth.send_transaction({'from': wallet.address,
                              'to': '0xFc11E697f23E5CbBeD3c59aC249955da57e57672', 
                              'value': hex(int(0.1 * 1e18))}) # Send us some Goerli ETH :)
atomic_tx = ew3.eulith_commit_transaction()
tx = ew3.eth.send_transaction(atomic_tx)
receipt1 = ew3.eth.wait_for_transaction_receipt(tx)

ew3.v0.start_atomic_transaction(wallet.address, safe_address)
ew3.eth.send_transaction({'from': wallet.address,
                              'to': '0xFc11E697f23E5CbBeD3c59aC249955da57e57672', 
                              'value': hex(int(0.7 * 1e18))})
atomic_tx = ew3.eulith_commit_transaction()
tx = ew3.eth.send_transaction(atomic_tx)
receipt2 = ew3.eth.wait_for_transaction_receipt(tx)

ew3.v0.start_atomic_transaction(wallet.address, safe_address)
ew3.eth.send_transaction({'from': wallet.address,
                              'to': '0xFc11E697f23E5CbBeD3c59aC249955da57e57672', 
                              'value': hex(int(1.25 * 1e18))})
atomic_tx = ew3.eulith_commit_transaction()
tx = ew3.eth.send_transaction(atomic_tx)
receipt3 = ew3.eth.wait_for_transaction_receipt(tx)

print(receipt1)
print(receipt2)
print(receipt3)

```

#### Second example
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
ew3.eth.send_transaction({'from': wallet.address,
                              'to': '0xFc11E697f23E5CbBeD3c59aC249955da57e57672', 
                              'value': hex(int(0.1 * 1e18))}) # Send us some Goerli ETH :)
ew3.eth.send_transaction({'from': wallet.address,
                              'to': '0xFc11E697f23E5CbBeD3c59aC249955da57e57672', 
                              'value': hex(int(0.7 * 1e18))})
ew3.eth.send_transaction({'from': wallet.address,
                              'to': '0xFc11E697f23E5CbBeD3c59aC249955da57e57672', 
                              'value': hex(int(1.25 * 1e18))})

ew3.v0.commit_atomic_transaction()
atomic_tx = ew3.eulith_commit_transaction()
tx = ew3.eth.send_transaction(atomic_tx)
receipt = ew3.eth.wait_for_transaction_receipt(tx)

print(receipt)
```


The DeFi Armor policy is applied when the atomic transaction is committed.

# DeFi Armor Utility Commands

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

## Vault (Gnosis Safe) Utility Commands
Armor can't work without its vault (Gnosis Safe). We have some basic utility commands to do basic transfers in and out
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
## `Connecting to Ledger`
If the command hangs on `Connecting to Ledger` for more than a second or two, kill the command with
Ctrl+C and re-run it again.

If the issue recurs, try plugging the Ledger into a different port of your machine.

## `We can't execute this request`
This error happens often on Arbitrum because of limited bandwidth in the sequencer (external to Eulith). Retry the request.

## `Intrinsic gas too low`
You need to add more gas to the tx with --gas... you'd be shocked how much gas Arbitrum will require, for example.

## `Insufficient funds`
You don't have enough ETH in your wallet to cover the cost of the proposed transaction

## `Connection aborted`
This error happens often on Arbitrum because of limited bandwidth in the sequencer (external to Eulith). Retry the request.

## `On-Chain: Fail with error 'Create2 call failed'`
Your tx ran out of gas. You need to specify more gas with `--gas <GAS AMOUNT>`. Example of this failure:
https://polygonscan.com/tx/0xd0d357abf434697fef2901ed2b85dff98846e8328ed69c3c88ca232915062168
