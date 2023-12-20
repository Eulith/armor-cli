"""
See the README file for instructions on using this CLI.
"""
import argparse
import os
import sys

from eulith_web3.eulith_web3 import EulithWeb3
from eulith_web3.kms import KmsSigner
from eulith_web3.ledger import LedgerSigner
from eulith_web3.signing import construct_signing_middleware, LocalSigner
from eulith_web3.trezor import TrezorSigner

from safe_utils import get_safe_balance, handle_start_transfer, handle_approve_hash, handle_execute_transfer

DUMMY_WALLET_TYPE = "dummy"
KMS_WALLET_TYPE = "kms"
LEDGER_WALLET_TYPE = "ledger"
TREZOR_WALLET_TYPE = "trezor"
PLAIN_TEXT_WALLET_TYPE = "text"
WALLET_TYPES = [DUMMY_WALLET_TYPE, KMS_WALLET_TYPE, LEDGER_WALLET_TYPE, TREZOR_WALLET_TYPE, PLAIN_TEXT_WALLET_TYPE]

MAINNET_NETWORK_TYPE = "mainnet"
ARBITRUM_NETWORK_TYPE = "arb"
GOERLI_NETWORK_TYPE = "goerli"
POLY_NETWORK_TYPE = "poly"
DEV_NETWORK_TYPE = "dev"
NETWORK_TYPES = [MAINNET_NETWORK_TYPE, ARBITRUM_NETWORK_TYPE, GOERLI_NETWORK_TYPE, POLY_NETWORK_TYPE, DEV_NETWORK_TYPE]


def print_banner():
    print(
        """ 
              ___           ___           ___                   ___           ___     
             /\  \         /\__\         /\__\      ___        /\  \         /\__\    
            /::\  \       /:/  /        /:/  /     /\  \       \:\  \       /:/  /    
           /:/\:\  \     /:/  /        /:/  /      \:\  \       \:\  \     /:/__/     
          /::\~\:\  \   /:/  /  ___   /:/  /       /::\__\      /::\  \   /::\  \ ___ 
         /:/\:\ \:\__\ /:/__/  /\__\ /:/__/     __/:/\/__/     /:/\:\__\ /:/\:\  /\__\\
         \:\~\:\ \/__/ \:\  \ /:/  / \:\  \    /\/:/  /       /:/  \/__/ \/__\:\/:/  /
          \:\ \:\__\    \:\  /:/  /   \:\  \   \::/__/       /:/  /           \::/  / 
           \:\ \/__/     \:\/:/  /     \:\  \   \:\__\       \/__/            /:/  /  
            \:\__\        \::/  /       \:\__\   \/__/                       /:/  /   
             \/__/         \/__/         \/__/                               \/__/    \n\n
        """)


def deploy_armor(ew3, wallet, auth_address, args):
    print(
        "This operation is expensive (potentially 0.3 ETH or more on mainnet depending on gas price)."
    )
    print()
    if not confirm("Are you sure you wish to continue [yes/no]? "):
        print()
        bail("operation aborted")

    armor_address, safe_address = ew3.v0.deploy_new_armor(
        ew3.to_checksum_address(auth_address),
        {
            "from": wallet.address,
            "gas": args.gas,
        },
    )
    print(f"Armor address: {armor_address}")
    print(f"Safe address:  {safe_address}")


def sign_armor_as_owner(ew3, wallet, auth_address, args):
    validate_addresses([auth_address])

    print("When prompted, please sign the request")
    status = ew3.v0.submit_enable_module_signature(auth_address, wallet)
    if not status:
        bail("failed to submit enable module signature")


def get_owner_signatures(ew3, wallet, auth_address, args):
    validate_addresses([auth_address])
    signatures = ew3.v0.get_accepted_enable_armor_signatures(auth_address)

    for s in signatures:
        print(s)


def show_wallet_address(ew3, wallet, auth_address, args):
    print(f'Your connected wallet address is {ew3.wallet_address}')


def enable_armor(ew3, wallet, auth_address, args):
    threshold = args.threshold
    owner_addresses = args.owner_addresses
    validate_addresses(owner_addresses)

    if len(owner_addresses) == 0:
        bail("at least one owner address must be supplied")

    if threshold < 1:
        bail("threshold must be at least 1")

    if threshold > len(owner_addresses):
        bail("threshold cannot be greater than the number of owners")

    print("When prompted, please sign transaction.")
    status = ew3.v0.enable_armor(
        auth_address,
        threshold,
        owner_addresses,
        {
            "from": wallet.address,
            "gas": args.gas,
        },
    )
    if not status:
        bail("failed to submit enable Armor module")


def submit_setup_safe_hash(ew3, wallet, auth_address, args):
    status, r = ew3.eulith_service.submit_enable_safe_tx_hash(args.tx_hash, has_ace=False)
    if status:
        print('Successfully processed setup safe hash')
    else:
        print(f'Unable to process setup safe hash, response came back {r}')


def addresses(ew3, wallet, auth_address, args):
    armor_address, safe_address = ew3.v0.get_armor_and_safe_addresses(auth_address)
    print(f"Armor address: {armor_address}")
    print(f"Safe address:  {safe_address}")


def create_whitelist(ew3, wallet, auth_address, args):
    list_id = ew3.v0.create_draft_client_whitelist(auth_address, args.addresses)
    print(f"Created draft client whitelist with ID {list_id}.")


def append_whitelist(ew3: EulithWeb3, wallet, auth_address, args):
    list_id = ew3.v0.append_to_draft_client_whitelist(auth_address, args.addresses, args.chain_id)
    print(f"Successfully appended to whitelist with ID: {list_id}")


def sign_whitelist(ew3, wallet, auth_address, args):
    print("When prompted, please sign transaction.")
    status = ew3.v0.submit_draft_client_whitelist_signature(args.list_id, wallet)
    if not status:
        print("Signature submitted, but threshold of owners not yet reached.")
    else:
        print(
            "Signature submitted and threshold of owners reached. Whitelist is enabled!"
        )


def get_whitelist(ew3, wallet, auth_address, args):
    whitelist = ew3.v0.get_current_client_whitelist(auth_address, args.chain_id)
    if whitelist is not None:
        active = whitelist.get('active')
        draft = whitelist.get('draft')
        chain_id = whitelist.get('chain_id')

        print(f'For chain id {chain_id} found whitelists:\n')
        print(f'Active: {active}')
        print(f'Draft: {draft}\n')


def getenv_or_bail(key):
    value = os.environ.get(key)
    if not value:
        bail(f"you must set {key} as an environment variable")

    return value


def bail(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def confirm(msg):
    yesno = input(msg)
    yesno = yesno.strip().lower()
    return yesno.startswith("y")


def get_kms_wallet():
    import boto3

    env_key = "AWS_CREDENTIALS_PROFILE_NAME"
    aws_credentials_profile_name = os.environ.get(env_key)
    if not aws_credentials_profile_name:
        bail(
            "if using wallet type {KMS_WALLET_TYPE!r}, {env_key} environment variable must be set"
        )

    env_key = "EULITH_KMS_KEY"
    kms_key_name = os.environ.get(env_key)
    if not kms_key_name:
        bail(
            "if using wallet type {KMS_WALLET_TYPE!r}, {env_key} environment variable must be set"
        )

    session = boto3.Session(profile_name=aws_credentials_profile_name)

    formatted_key_name = f"alias/{kms_key_name}"
    client = session.client("kms")
    return KmsSigner(client, formatted_key_name)


def get_eulith_url(network_type):
    if network_type == MAINNET_NETWORK_TYPE:
        return "https://eth-main.eulithrpc.com/v0"
    elif network_type == ARBITRUM_NETWORK_TYPE:
        return "https://arb-main.eulithrpc.com/v0"
    elif network_type == GOERLI_NETWORK_TYPE:
        return "https://eth-goerli.eulithrpc.com/v0"
    elif network_type == POLY_NETWORK_TYPE:
        return "https://poly-main.eulithrpc.com/v0"
    elif network_type == DEV_NETWORK_TYPE:
        return "http://localhost:7777/v0"
    else:
        bail(f"unsupported network type {network_type!r}")


def validate_addresses(addresses):
    for address in addresses:
        if address and not address.startswith("0x"):
            bail(f"address must be a valid hex number starting with '0x': {address}")


if __name__ == "__main__":
    env_wallet_type = os.environ.get("EULITH_WALLET_TYPE")

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="subcommands")

    parser_deploy_armor = subparsers.add_parser(
        "deploy-armor", help="Deploy a new Armor contract and Gnosis Safe"
    )
    parser_deploy_armor.add_argument("--gas", type=int, default=2500000)
    parser_deploy_armor.set_defaults(func=deploy_armor)

    parser_sign_armor = subparsers.add_parser(
        "sign-armor-as-owner",
        help="Sign the Armor contract with an owner wallet of the Safe",
    )
    parser_sign_armor.set_defaults(func=sign_armor_as_owner)

    parser_get_existing_signatures = subparsers.add_parser(
        "get-owner-signatures",
        help="Get a list of as-of-yet accepted owner signatures"
    )
    parser_get_existing_signatures.set_defaults(func=get_owner_signatures)

    parser_enable_armor = subparsers.add_parser(
        "enable-armor", help="Enable the Armor contract as a module on the Safe"
    )
    parser_enable_armor.add_argument("--threshold", type=int)
    parser_enable_armor.add_argument("--owner-addresses", nargs="*", metavar="ADDR")
    parser_enable_armor.add_argument("--gas", type=int, default=500000)
    parser_enable_armor.set_defaults(func=enable_armor)

    parser_submit_setup_safe_hash = subparsers.add_parser(
        "submit-setup-safe", help="The hash of the tx where you set up the Safe and enabled armor"
    )
    parser_submit_setup_safe_hash.add_argument("--tx-hash", type=str, required=True)
    parser_submit_setup_safe_hash.set_defaults(func=submit_setup_safe_hash)

    parser_create_whitelist = subparsers.add_parser(
        "create-whitelist",
        help="Create a new draft whitelist to be signed by Safe owners",
    )
    parser_create_whitelist.add_argument("--addresses", nargs="*", metavar="ADDR")
    parser_create_whitelist.set_defaults(func=create_whitelist)

    parser_create_whitelist = subparsers.add_parser(
        "append-whitelist",
        help="Append to an existing whitelist draft",
    )
    parser_create_whitelist.add_argument("--addresses", nargs="*", metavar="ADDR", required=True)
    parser_create_whitelist.add_argument("--chain-id", type=int, required=False, default=None)
    parser_create_whitelist.set_defaults(func=append_whitelist)

    parser_sign_whitelist = subparsers.add_parser(
        "sign-whitelist", help="Sign a previously-created whitelist"
    )
    parser_sign_whitelist.add_argument("--list-id", type=int)
    parser_sign_whitelist.set_defaults(func=sign_whitelist)

    parser_get_whitelist = subparsers.add_parser(
        "get-whitelist", help="Retrieve the contents of a whitelist"
    )
    parser_get_whitelist.add_argument("--chain-id", type=int, required=False, default=None)
    parser_get_whitelist.set_defaults(func=get_whitelist)

    parser_addresses = subparsers.add_parser(
        "addresses", help="Get Armor and Safe addresses"
    )
    parser_addresses.set_defaults(func=addresses)

    parser_get_safe_balance = subparsers.add_parser(
        "safe-balance",
        help="Get a specified ERC20 balance of your safe"
    )
    parser_get_safe_balance.add_argument("--safe", type=str, help="the address of your safe", required=True)
    parser_get_safe_balance.add_argument("--token", type=str, help="the ticker symbol or address of the token", required=True)
    parser_get_safe_balance.set_defaults(func=get_safe_balance)

    parser_get_transfer_hash = subparsers.add_parser(
        "start-safe-transfer",
        help="Start a transfer (ERC20 tokens or native) from your safe to a specified wallet"
    )
    parser_get_transfer_hash.add_argument("--safe", type=str, help="the address of your safe", required=True)
    parser_get_transfer_hash.add_argument("--token", type=str, help="the ticker symbol or address of the token (use the null address for native)", required=True)
    parser_get_transfer_hash.add_argument("--dest", type=str, help="the address of the destination", required=True)
    parser_get_transfer_hash.add_argument("--amount", type=float, help="the amount you want to transfer", required=True)
    parser_get_transfer_hash.set_defaults(func=handle_start_transfer)

    parser_execute_safe_transfer = subparsers.add_parser(
        "execute-safe-transfer",
        help="Execute a transfer (ERC20 tokens or native) from your safe to a specified wallet"
    )
    parser_execute_safe_transfer.add_argument("--safe", type=str, help="the address of your safe", required=True)
    parser_execute_safe_transfer.add_argument("--token", type=str,
                                          help="the ticker symbol or address of the token (use the null address for native)",
                                          required=True)
    parser_execute_safe_transfer.add_argument("--dest", type=str, help="the address of the destination", required=True)
    parser_execute_safe_transfer.add_argument("--amount", type=float, help="the amount you want to transfer", required=True)
    parser_execute_safe_transfer.add_argument("--owners", nargs='+', help="the owners you approved the transaction hash with",
                                              required=True)
    parser_execute_safe_transfer.set_defaults(func=handle_execute_transfer)

    parser_approve_safe_hash = subparsers.add_parser(
        "safe-approve-hash",
        help="Approve tx hash for a Safe transaction"
    )
    parser_approve_safe_hash.add_argument("--safe", type=str, help="the address of your safe", required=True)
    parser_approve_safe_hash.add_argument("--hash", type=str,
                                          help="the hash of the tx you would like to approve",
                                          required=True)
    parser_approve_safe_hash.set_defaults(func=handle_approve_hash)

    parser_approve_safe_hash = subparsers.add_parser(
        "show-wallet",
        help="Show the address of the connected wallet"
    )
    parser_approve_safe_hash.set_defaults(func=show_wallet_address)

    args = parser.parse_args()

    eulith_token = getenv_or_bail("EULITH_TOKEN")
    auth_address = os.environ.get("EULITH_TRADING_ADDRESS")
    validate_addresses([auth_address])

    network_type = getenv_or_bail("EULITH_NETWORK_TYPE")
    if network_type not in NETWORK_TYPES:
        network_types_string = ", ".join(NETWORK_TYPES)
        bail(
            f"invalid network type {network_type!r}, expected one of: {network_types_string}"
        )

    wallet_type = getenv_or_bail("EULITH_WALLET_TYPE")

    if wallet_type and wallet_type not in WALLET_TYPES:
        wallet_types_string = ", ".join(WALLET_TYPES)
        bail(
            f"invalid wallet type {wallet_type!r}, expected one of: {wallet_types_string}"
        )

    eulith_url = get_eulith_url(network_type)

    if wallet_type == KMS_WALLET_TYPE:
        wallet = get_kms_wallet()
    elif wallet_type == LEDGER_WALLET_TYPE:
        print("Connecting to Ledger")
        wallet = LedgerSigner()
        print("Connected to Ledger")
        print()
    elif wallet_type == TREZOR_WALLET_TYPE:
        print("Connecting to Trezor")
        wallet = TrezorSigner()
        print("Connected to Trezor\n")
    elif wallet_type == PLAIN_TEXT_WALLET_TYPE:
        private_key = getenv_or_bail("PRIVATE_KEY")
        wallet = LocalSigner(private_key)
    else:
        bail(f"unsupported wallet type {wallet_type!r}")

    with EulithWeb3(
        eulith_url=eulith_url,
        eulith_token=eulith_token,
        signing_middle_ware=construct_signing_middleware(wallet),
    ) as ew3:
        if network_type == POLY_NETWORK_TYPE:
            from web3.middleware import geth_poa_middleware
            ew3.middleware_onion.inject(geth_poa_middleware, layer=0)

        try:
            args.func(ew3, wallet, auth_address, args)
        except AttributeError:
            print_banner()
            print("Did not receive any commands. Try running ./run.sh -h for help")
