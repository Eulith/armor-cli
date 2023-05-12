"""
See the README file for instructions on using this CLI.
"""
import argparse
import os
import sys

from eulith_web3.eulith_web3 import EulithWeb3
from eulith_web3.kms import KmsSigner
from eulith_web3.ledger import LedgerSigner
from eulith_web3.signing import construct_signing_middleware

DUMMY_WALLET_TYPE = "dummy"
KMS_WALLET_TYPE = "kms"
LEDGER_WALLET_TYPE = "ledger"
WALLET_TYPES = [DUMMY_WALLET_TYPE, KMS_WALLET_TYPE, LEDGER_WALLET_TYPE]

MAINNET_NETWORK_TYPE = "mainnet"
ARBITRUM_NETWORK_TYPE = "arb"
GOERLI_NETWORK_TYPE = "goerli"
NETWORK_TYPES = [MAINNET_NETWORK_TYPE, ARBITRUM_NETWORK_TYPE, GOERLI_NETWORK_TYPE]


def deploy_armor(ew3, wallet, auth_address, args):
    print(
        "This operation is expensive (potentially 0.3 ETH or more on mainnet depending on gas price)."
    )
    print()
    if not confirm("Are you sure you wish to continue [yes/no]? "):
        print()
        bail("operation aborted")

    armor_address, safe_address = ew3.v0.deploy_new_armor(
        # TODO: Should take auth_address as a parameter.
        ew3.to_checksum_address(wallet.address),
        {
            "from": wallet.address,
            "gas": args.gas,
        },
    )
    print(f"Armor address: {armor_address}")
    print(f"Safe address:  {safe_address}")


def sign_armor_as_owner(ew3, wallet, auth_address, args):
    validate_addresses([auth_address])

    print("When prompted, please sign transaction.")
    status = ew3.v0.submit_enable_module_signature(auth_address, wallet)
    if not status:
        bail("failed to submit enable module signature")


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


def addresses(ew3, wallet, auth_address, args):
    armor_address, safe_address = ew3.v0.get_armor_and_safe_addresses(wallet.address)
    print(f"Armor address: {armor_address}")
    print(f"Safe address:  {safe_address}")


def create_whitelist(ew3, wallet, auth_address, args):
    list_id = ew3.v0.create_draft_client_whitelist(auth_address, args.addresses)
    print(f"Created draft client whitelist with ID {list_id}.")


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
    whitelist = ew3.v0.get_current_client_whitelist(auth_address, is_draft=args.draft)
    if whitelist is not None:
        print(whitelist)
    else:
        if args.draft:
            print("No draft whitelist found. (Try without --draft flag?)")
        else:
            print("No published whitelist found. (Try with --draft flag?)")


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


class DummyEw3:
    def __getattr__(self, name):
        if name == "v0":
            return self
        else:
            return self.make_function(name)

    def make_dummy_function(self, name):
        def dummy_function(self, *args, **kwargs):
            print(f"[DummyEw3] Calling function {name}")
            return ["dummy address 1", "dummy address 2"]

        return dummy_function


class DummyWallet:
    def __init__(self):
        self.address = "dummy wallet address"


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
    else:
        bail(f"unsupported network type {network_type!r}")


def validate_addresses(addresses):
    for address in addresses:
        if not address.startswith("0x"):
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

    parser_enable_armor = subparsers.add_parser(
        "enable-armor", help="Enable the Armor contract as a module on the Safe"
    )
    parser_enable_armor.add_argument("--threshold", type=int)
    parser_enable_armor.add_argument("--owner-addresses", nargs="*", metavar="ADDR")
    parser_enable_armor.add_argument("--gas", type=int, default=500000)
    parser_enable_armor.set_defaults(func=enable_armor)

    parser_create_whitelist = subparsers.add_parser(
        "create-whitelist",
        help="Create a new draft whitelist to be signed by Safe owners",
    )
    parser_create_whitelist.add_argument("--addresses", nargs="*", metavar="ADDR")
    parser_create_whitelist.set_defaults(func=create_whitelist)

    parser_sign_whitelist = subparsers.add_parser(
        "sign-whitelist", help="Sign a previously-created whitelist"
    )
    parser_sign_whitelist.add_argument("--list-id", type=int)
    parser_sign_whitelist.set_defaults(func=sign_whitelist)

    parser_get_whitelist = subparsers.add_parser(
        "get-whitelist", help="Retrieve the contents of a whitelist"
    )
    parser_get_whitelist.add_argument(
        "--draft",
        action="store_true",
        help="Retrieve the draft whitelist instead of the published one",
    )
    parser_get_whitelist.set_defaults(func=get_whitelist)

    parser_addresses = subparsers.add_parser(
        "addresses", help="Get Armor and Safe addresses"
    )
    parser_addresses.set_defaults(func=addresses)

    args = parser.parse_args()

    refresh_token = getenv_or_bail("EULITH_REFRESH_TOKEN")
    auth_address = getenv_or_bail("EULITH_AUTH_ADDRESS")
    validate_addresses([auth_address])

    network_type = getenv_or_bail("EULITH_NETWORK_TYPE")
    if network_type not in NETWORK_TYPES:
        network_types_string = ", ".join(NETWORK_TYPES)
        bail(
            f"invalid network type {network_type!r}, expected one of: {network_types_string}"
        )

    wallet_type = getenv_or_bail("EULITH_WALLET_TYPE")
    if wallet_type not in WALLET_TYPES:
        wallet_types_string = ", ".join(WALLET_TYPES)
        bail(
            f"invalid wallet type {wallet_type!r}, expected one of: {wallet_types_string}"
        )

    if wallet_type == DUMMY_WALLET_TYPE:
        wallet = DummyWallet()
        ew3 = DummyEw3()
    else:
        eulith_url = get_eulith_url(network_type)

        if wallet_type == KMS_WALLET_TYPE:
            wallet = get_kms_wallet()
        elif wallet_type == LEDGER_WALLET_TYPE:
            print("Connecting to Ledger")
            wallet = LedgerSigner()
            print("Connected to Ledger")
            print()
        else:
            bail(f"unsupported wallet type {wallet_type!r}")

        ew3 = EulithWeb3(
            eulith_url=eulith_url,
            eulith_refresh_token=refresh_token,
            signing_middle_ware=construct_signing_middleware(wallet),
        )

    args.func(ew3, wallet, auth_address, args)
