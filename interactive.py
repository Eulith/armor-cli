from typing import List

from eulith_web3.eulith_web3 import EulithWeb3
from eulith_web3.ledger import LedgerSigner
from eulith_web3.signing import LocalSigner, construct_signing_middleware
from eulith_web3.trezor import TrezorSigner
from eulith_web3.contract_bindings.safe.i_safe import ISafe

from armor import print_banner

DEPLOYMENT_GAS_VALUES = {
    "celo-main": 5000000,
    "eth-main": 1000000,
    "arb-main": 20000000,
    "opt-main": 20000000,
    "poly-main": 1000000,
}


class UnsupportedWalletException(Exception):
    pass


def print_wallet_types():
    print(
        "For a detailed list of the relevant wallets (signers) involved in DeFi Armor, please see the README.md"
    )
    print("To summarize:")
    print(
        "\t - DEPLOYMENT: this wallet will be used to execute the setup transactions. It can be any wallet with gas."
    )
    print(
        "\t - TRADING KEY: the wallet authorized to take trading actions on behalf of your Safe"
    )
    print(
        "\t - OWNER(s): the wallet(s) that own the Safe. A threshold of these wallets is required to "
        "authorize root access on the Safe"
    )


def input_with_retry(prompt: str, acceptable_responses: List):
    r = input(prompt).lower()

    while r not in acceptable_responses:
        print(
            f"{r} is not a valid response, please enter one of: {acceptable_responses}"
        )
        r = input(prompt).lower()

    return r


def run_get_wallet(input_str, acceptable_responses=None):
    if acceptable_responses is None:
        acceptable_responses = ["ledger", "trezor", "text"]

    wallet_type = input_with_retry(input_str, acceptable_responses)

    if wallet_type == "ledger":
        print("\nPlease connect your ledger now and press ENTER when ready")
        input()
        wallet = LedgerSigner()
    elif wallet_type == "trezor":
        print("\nPlease connect your trezor now and press ENTER when ready")
        input()
        wallet = TrezorSigner()
    elif wallet_type == "text":
        private_key = input(
            "\nPlease enter your private key. NOTE: this key is not sent over the network, "
            "it is only used locally for signing"
        )
        wallet = LocalSigner(private_key)
    else:
        raise UnsupportedWalletException("unsupported wallet type")

    return wallet


def run_deploy_new_armor(network_id: str, eulith_token: str):
    wallet = run_get_wallet(
        f"\nWhat type of wallet is your DEPLOYMENT wallet? (ledger, trezor, text) : "
    )

    print(
        f"\nDetected {wallet.address} as the DEPLOYMENT wallet address. \nPress enter to proceed."
    )
    input()

    auth_address = input("What is the address of your TRADING KEY? :  ")

    with EulithWeb3(
        f"https://{network_id}.eulithrpc.com/v0",
        eulith_token,
        construct_signing_middleware(wallet),
    ) as ew3:
        if network_id == "celo-main" or network_id == "poly-main":
            from web3.middleware import geth_poa_middleware

            ew3.middleware_onion.inject(geth_poa_middleware, layer=0)

        new_or_existing = input_with_retry(
            "\nAre we setting up DeFi Armor on a new Safe (n) or existing Safe? (e) :  ",
            ["n", "e"],
        )
        if new_or_existing == "n":
            exist_safe = None
            print("\nProceeding with new Safe deployment...")
        else:
            given_safe = input("\nGreat, please enter the existing Safe address :  ")
            try:
                exist_safe = ew3.to_checksum_address(given_safe)
            except Exception as _e:
                print(
                    "That does not appear to be a valid safe address. Please double check and start over"
                )
                exit(1)
            print(f"\nProceeding with existing Safe deployment")

        armor_address, safe_address = ew3.v0.deploy_new_armor(
            authorized_trading_address=ew3.to_checksum_address(auth_address),
            override_tx_params={
                "from": wallet.address,
                "gas": DEPLOYMENT_GAS_VALUES.get(network_id),
            },
            existing_safe_address=exist_safe,
        )

        print(f"New armor address: {armor_address}")
        print(f"New safe address:  {safe_address}")


def run_submit_owner_signature(network_id: str, eulith_token: str):
    trading_address = input(
        "What trading key would you like to submit an owner signature for? : "
    )
    with EulithWeb3(
        f"https://{network_id}.eulithrpc.com/v0",
        eulith_token,
    ) as ew3:
        if network_id == "celo-main" or network_id == "poly-main":
            from web3.middleware import geth_poa_middleware

            ew3.middleware_onion.inject(geth_poa_middleware, layer=0)

        existing_signatures = ew3.v0.get_accepted_enable_armor_signatures(
            trading_address
        )
        if len(existing_signatures) > 0:
            print("Discovered existing owner signatures for this account: ")
            for i, e in enumerate(existing_signatures):
                print(f'Owner {i}: {e.get("owner_address")}')

            cont = input_with_retry(
                "\nWould you like to add more signatures? (y, n) : ", ["y", "n"]
            )
            if cont == "n":
                print("Goodbye")
                exit(0)

        another_wallet = True
        while another_wallet:
            try:
                wallet = run_get_wallet(
                    f"\nWhat type of wallet is your next OWNER wallet? Or enter `q` to quit. (ledger, trezor, text, q) : ",
                    acceptable_responses=["ledger", "trezor", "text", "q"],
                )
            except UnsupportedWalletException as e:
                another_wallet = False
                continue

            print(f"\nDetected wallet address: {wallet.address}")
            print(f"Press ENTER to continue")
            input()

            print("\nAwaiting signature....")
            status = ew3.v0.submit_enable_module_signature(trading_address, wallet)
            if status:
                print(f"Signature accepted!")
            else:
                print(f"Signature failed")
                exit(1)

            existing_signatures = ew3.v0.get_accepted_enable_armor_signatures(
                trading_address
            )
            print("\nNow have signatures for owners:")
            for i, e in enumerate(existing_signatures):
                print(f'Owner {i}: {e.get("owner_address")}')


def run_enable_armor_new_safe(network_id: str, eulith_token: str):
    trading_address = input("Which trading key are we enabling Armor for? : ")

    deployment_wallet = run_get_wallet(
        "What kind of wallet would you like to use for DEPLOYMENT? : "
    )
    print(f"Parsed deployment wallet address: {deployment_wallet.address}")

    with EulithWeb3(
        f"https://{network_id}.eulithrpc.com/v0",
        eulith_token,
        construct_signing_middleware(deployment_wallet),
    ) as ew3:
        if network_id == "celo-main" or network_id == "poly-main":
            from web3.middleware import geth_poa_middleware

            ew3.middleware_onion.inject(geth_poa_middleware, layer=0)

        existing_signatures = ew3.v0.get_accepted_enable_armor_signatures(
            trading_address
        )
        signatures_for_owners = []
        if len(existing_signatures) > 0:
            print("\n\nDiscovered existing owner signatures for this account: ")
            for i, e in enumerate(existing_signatures):
                print(f'Owner {i}: {e.get("owner_address")}')
                signatures_for_owners.append(e.get("owner_address"))

            print(
                "\nIf you would like to provide signatures for more owners signatures on this account, "
                "you'll need to re-run this script and select option (2)"
            )
            print(
                "\nNOTE: You do NOT need signatures from all your owners. "
                "You only need a sufficient threshold of owner signatures to proceed\n"
            )
        else:
            print(
                "Could not find any valid owner signatures. Cannot enable Armor with no owner signatures. Exiting."
            )
            exit(1)

        more_owners = "a"
        full_owner_list = set(signatures_for_owners)

        while more_owners == "a":
            additional_owner_input = input(
                "Please input additional non-signing owners, separated by commas (ex: 0x123,0x456,0x789) : "
            )
            additional_owners = additional_owner_input.split(",")

            for a in additional_owners:
                try:
                    parsed_address = ew3.to_checksum_address(a)
                    full_owner_list.add(parsed_address)
                except Exception:
                    print(f"Could not parse {a} as a valid address. Ignoring.")

            print("\nYou are about to enable Armor with these owners: ")
            for i, o in enumerate(full_owner_list):
                print(f"Owner {i}: {o}")

            more_owners = input_with_retry(
                "\nTo continue, press ENTER. To add additional owners, press `a` : ",
                ["", "a"],
            )

        threshold = int(
            input(
                "\nPlease enter the threshold of owner signatures you would like (ex: 2) : "
            )
        )

        has_ace_input = input_with_retry(
            "Do you intend to run an ACE with this account? (y, n) : ", ["y", "n"]
        )
        has_ace = has_ace_input == "y"

        print("\n\n~~ SUMMARY ~~")
        print(f"Threshold:   {threshold}")
        print(f"Has ACE:     {has_ace}")
        print(f"Owners:      {full_owner_list}")

        input(f"\nTo continue, press ENTER...\n")

        print(f"Awaiting signature and sending transaction...")

        status = ew3.v0.enable_armor_for_new_safe(
            trading_address,
            threshold,
            list(full_owner_list),
            {
                "gas": DEPLOYMENT_GAS_VALUES[network_id],
                "from": deployment_wallet.address,
            },
        )

        if status:
            print(f"~~ Armor successfully enabled! ~~")
        else:
            print(f"Something went wrong!")


def run_enable_armor_existing_safe(network_id: str, eulith_token: str):
    trading_address = input("Which trading key are we enabling Armor for? : ")

    deployment_wallet = run_get_wallet(
        "What kind of wallet would you like to use for DEPLOYMENT? : "
    )
    print(f"Parsed deployment wallet address: {deployment_wallet.address}")

    with EulithWeb3(
        f"https://{network_id}.eulithrpc.com/v0",
        eulith_token,
        construct_signing_middleware(deployment_wallet),
    ) as ew3:
        if network_id == "celo-main" or network_id == "poly-main":
            from web3.middleware import geth_poa_middleware

            ew3.middleware_onion.inject(geth_poa_middleware, layer=0)

        existing_signatures = ew3.v0.get_accepted_enable_armor_signatures(
            trading_address
        )
        signatures_for_owners = []

        sa, aa = ew3.v0.get_armor_and_safe_addresses(trading_address)
        safe = ISafe(ew3, sa)

        threshold = safe.get_threshold()
        owners = safe.get_owners()

        if len(existing_signatures) > 0:
            print("\n\nDiscovered existing owner signatures for this account: ")
            for i, e in enumerate(existing_signatures):
                print(f'Owner {i}: {e.get("owner_address")}')
                signatures_for_owners.append(e.get("owner_address"))

            print(
                "\nIf you would like to provide signatures for more owners signatures on this account, "
                "you'll need to re-run this script and select option (2)"
            )

        print(f'\nThe threshold for this safe is: {threshold}')
        print(f'The owners are: {owners}\n')

        input('Press ENTER to continue...')

        status = ew3.v0.enable_armor_for_existing_safe(
            trading_address,
            {
                "gas": DEPLOYMENT_GAS_VALUES[network_id],
                "from": deployment_wallet.address,
            },
        )

        if status:
            print(f"~~ Armor successfully enabled! ~~")
        else:
            print(f"Something went wrong!")


def main():
    print_banner()
    print("~~ Welcome to the DeFi Armor interactive setup script ~~")
    print(
        f"If you prefer to use a regular CLI, please see the README.md for further instructions"
    )
    print("\n\n")

    print_wallet_types()

    eulith_token = input("\n\nPlease enter a valid Eulith API Token: ")

    network = input_with_retry(
        "\nWhat network? (eth, celo, arb, opt, poly): ",
        ["celo", "eth", "arb", "opt", "poly"],
    )
    network_id = f"{network}-main"

    print("\nWhat would you like to do?\n")
    print("(1) Deploy new armor")
    print("(2) Submit owner signatures")
    print("(3) Enable armor for new Safe\n")
    print("(4) Enable armor for existing Safe")
    action = int(input_with_retry(": ", ["1", "2", "3"]))

    if action == 1:
        run_deploy_new_armor(network_id, eulith_token)
    elif action == 2:
        run_submit_owner_signature(network_id, eulith_token)
    elif action == 3:
        run_enable_armor_new_safe(network_id, eulith_token)
    elif action == 4:
        run_enable_armor_existing_safe(network_id, eulith_token)


if __name__ == "__main__":
    main()
