from typing import List

import web3
from web3.types import ChecksumAddress

from eulith_web3.contract_bindings.safe.i_safe import ISafe
from eulith_web3.erc20 import EulithERC20
from eulith_web3.eulith_web3 import EulithWeb3


NULL_ADDRESS = '0x0000000000000000000000000000000000000000'


def int_to_big_endian(value: int) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8 or 1, "big")


def big_endian_to_int(value: bytes) -> int:
    return int.from_bytes(value, "big")


def pad32(value: bytes) -> bytes:
    return value.rjust(32, b'\x00')


def int_to_byte(value: int) -> bytes:
    return bytes([value])


def approve_tx_hash(ew3: EulithWeb3, tx_hash: bytes, safe_addr: str) -> str:
    safe = ISafe(ew3, ew3.to_checksum_address(safe_addr))

    approve_tx = safe.approve_hash(tx_hash, {
        'from': ew3.wallet_address,
        'gas': 300000
    })

    r = ew3.eth.send_transaction(approve_tx)

    return r.hex()


def get_safe_balance(ew3, wallet, auth_address, args):
    token = get_token_address(ew3, args.token)
    safe = ew3.to_checksum_address(args.safe)

    tc = EulithERC20(ew3, token)
    bal = tc.balance_of_float(safe)

    print(f'\nYour safe has a balance of {bal} for token {tc.symbol} ({tc.address}).')


def handle_start_transfer(ew3, wallet, auth_address, args):
    safe = ew3.to_checksum_address(args.safe)
    token = get_token_address(ew3, args.token)
    amount = args.amount
    dest = ew3.to_checksum_address(args.dest)

    if token == NULL_ADDRESS:
        print(f'Starting a transfer of {amount} native token to {dest}')
        value = int(amount*1e18)
        data = b''
        to = dest
    else:
        erc = EulithERC20(ew3, token)
        print(f'Starting a transfer of {amount} {erc.symbol} ({erc.address}) to {dest}')
        value = 0
        tt = erc.transfer_float(dest, amount, {
            'from': safe,
            'gas': 0
        })
        data = bytearray.fromhex(tt.get('data')[2:])
        to = erc.address

    tx_hash = get_tx_hash(ew3, safe, to, value, data)

    safe = ISafe(ew3, safe)
    thresh = safe.get_threshold()

    print(f'Please approve this hash with at least {thresh} owners: 0x{tx_hash.hex()}\n')


def handle_execute_transfer(ew3, wallet, auth_address, args):
    safe = ew3.to_checksum_address(args.safe)
    token = get_token_address(ew3, args.token)
    amount = args.amount
    dest = ew3.to_checksum_address(args.dest)
    owners = args.owners

    if token == NULL_ADDRESS:
        print(f'Executing a transfer of {amount} native token from | SAFE: {safe} | ---> to {dest}')
        value = int(amount*1e18)
        data = b''
        bal_before = float(ew3.eth.get_balance(dest) / 1e18)
        to = dest
    else:
        erc = EulithERC20(ew3, token)
        print(f'Executing a transfer of {amount} {erc.symbol} ({erc.address}) from | SAFE: {safe} | ---> to {dest}')
        value = 0

        safe_bal_of_token = erc.balance_of_float(safe)
        assert safe_bal_of_token >= amount

        tt = erc.transfer_float(dest, amount, {
            'gas': 200000,
            'from': ew3.wallet_address
        })
        data = bytearray.fromhex(tt.get('data')[2:])
        bal_before = erc.balance_of_float(dest)
        to = erc.address

    input('\nPlease hit ENTER to proceed...\n')
    try:
        tx_hash = execute_tx(ew3, safe, to, value, data, owners)
    except web3.exceptions.ContractLogicError as e:
        print(f'Something went wrong with the execution, received error: {e}')
        exit(1)

    if token == NULL_ADDRESS:
        bal_now = float(ew3.eth.get_balance(dest) / 1e18)
    else:
        erc = EulithERC20(ew3, token)
        bal_now = erc.balance_of_float(dest)

    print(f'Successfully executed the transfer from safe {safe} at tx: {tx_hash}')
    print(f'Destination: {dest} had balance {bal_before} before the transfer, and now has balance: {bal_now}\n')


def handle_approve_hash(ew3, wallet, auth_address, args):
    safe = ew3.to_checksum_address(args.safe)
    to_approve = args.hash

    isafe = ISafe(ew3, safe)
    is_owner = isafe.is_owner(ew3.to_checksum_address(ew3.wallet_address))

    if not is_owner:
        print(f'Cannot approve a hash from a non-owner. {ew3.wallet_address} is not an owner of the specified safe.')
        exit(1)

    parsed_hash = bytearray.fromhex(to_approve[2:])

    tx_hash = approve_tx_hash(ew3, parsed_hash, safe)

    print(f'Successfully approved hash for owner: {ew3.wallet_address} at tx: {tx_hash}\n')



def get_tx_hash(ew3: EulithWeb3, safe_addr: str, to: str, value: int, data: bytes) -> bytes:
    """
    Note: This is a simplified abstraction over the full safe method. We do not handle any gas parameters
    in this method; they are set automatically by the estimation logic. If you would like to modify them, you can
    call the safe directly like we do below.

    :return: Transaction hash as bytes
    """

    safe = ISafe(ew3, ew3.to_checksum_address(safe_addr))

    nonce = safe.nonce()

    tx_hash = safe.get_transaction_hash(
        to,
        value,
        data,
        0,
        0,
        0,
        0,
        NULL_ADDRESS,
        NULL_ADDRESS,
        nonce
    )

    return tx_hash


def execute_tx(ew3: EulithWeb3, safe_addr: str, to: str, value: int, data: bytes, owners: List[str]) -> str:
    """
    This method assumes you have approved the tx hash generated by the specified tx parameters.

    Note: This is a simplified abstraction over the full safe method. We do not handle any gas parameters
    in this method; they are set automatically by the estimation logic. If you would like to modify them, you can
    call the safe directly like we do below.

    :return: Transaction hash of the executed transaction
    """
    safe = ISafe(ew3, ew3.to_checksum_address(safe_addr))

    signatures = bytearray()

    for o in owners:
        r = pad32(int_to_big_endian(int(ew3.to_checksum_address(o), 16)))
        s = pad32(int_to_big_endian(0))
        v = int_to_byte(1)

        encoded_sig = b''.join((r, s, v))

        signatures += encoded_sig

    tx = safe.exec_transaction(
        to,
        value,
        data,
        0,
        0,
        0,
        0,
        NULL_ADDRESS,
        NULL_ADDRESS,
        signatures,
        {
            'from': ew3.wallet_address
        }
    )

    # We systematically overestimate gas to prevent failure
    tx['gas'] = int(tx.get('gas', 200000) * 1.5)

    r = ew3.eth.send_transaction(tx)

    return r.hex()

def get_token_address(ew3: EulithWeb3, token: str) -> ChecksumAddress:
    if token.startswith("0x"):
        return ew3.to_checksum_address(args.token)
    else:
        erc20 = ew3.eulith_get_erc_token(token)
        return ew3.to_checksum_address(erc20.address)
