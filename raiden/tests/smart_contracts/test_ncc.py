# -*- coding: utf8 -*-
import pytest

from ethereum import tester
from ethereum import slogging
from ethereum.tester import ABIContract, TransactionFailed

from raiden.messages import Lock, DirectTransfer
from raiden.mtree import merkleroot
from raiden.utils import privtoaddr, sha3

log = slogging.getLogger(__name__)  # pylint: disable=invalid-name


def test_ncc(state, channel, token):  # pylint: disable=too-many-locals,too-many-statements
    # test tokens and distribute tokens
    assert token.balanceOf(tester.a0) == 10000
    assert token.balanceOf(tester.a1) == 0
    assert token.transfer(tester.a1, 5000) is True
    assert token.balanceOf(tester.a0) == 5000
    assert token.balanceOf(tester.a1) == 5000

    # test global variables
    assert channel.settleTimeout() == 30
    assert channel.assetAddress() == token.address.encode('hex')
    assert channel.opened() == 0
    assert channel.closed() == 0
    assert channel.settled() == 0

    # test participants variables changed when constructing
    assert channel.addressAndBalance()[0] == tester.a0.encode('hex')
    assert channel.addressAndBalance()[2] == tester.a1.encode('hex')

    # test atIndex()
    # private must be removed from the function in order to work
    # assert channel.atIndex(sha3('address1')[:20]) == 0
    # assert channel.atIndex(sha3('address2')[:20]) == 1

    # test deposit(uint)
    with pytest.raises(TransactionFailed):
        channel.deposit(30, sender=tester.k2)  # not participant

    assert token.balanceOf(channel.address) == 0
    assert token.approve(channel.address, 30) is True # allow the contract do deposit
    assert channel.addressAndBalance()[1] == 0
    with pytest.raises(TransactionFailed):
        channel.deposit(5001)
    channel.deposit(30)
    assert channel.addressAndBalance()[1] == 30
    assert token.balanceOf(channel.address) == 30
    assert token.balanceOf(tester.a0) == 4970
    assert channel.opened() == state.block.number

    # test open()
    # private must be removed from the function in order to work
    # assert channel.opened() == 0  # channel is not yet opened
    # channel.open()
    # assert channel.opened() > 0
    # assert channel.opened() <= state.block.number

    # test partner(address)
    # private must be removed from the function in order to work
    # assert channel.partner(sha3('address1')[:20]) == sha3('address2')[:20].encode('hex')
    # assert channel.partner(sha3('address2')[:20]) == sha3('address1')[:20].encode('hex')

    # test addressAndBalance()
    a1, d1, a2, d2 = channel.addressAndBalance()
    assert a1 == tester.a0.encode('hex')
    assert a2 == tester.a1.encode('hex')
    assert d1 == 30
    assert d2 == 0

    # test close(message)

    INITIATOR_PRIVKEY = tester.k0

    RECIPIENT_PRIVKEY = tester.k1
    RECIPIENT_ADDRESS = privtoaddr(RECIPIENT_PRIVKEY)

    ASSET_ADDRESS = token.address

    HASHLOCK = sha3(INITIATOR_PRIVKEY)
    LOCK_AMOUNT = 29
    LOCK_EXPIRATION = 31
    LOCK = Lock(LOCK_AMOUNT, LOCK_EXPIRATION, HASHLOCK)
    LOCKSROOT = merkleroot([
        sha3(LOCK.as_bytes),
    ])

    nonce = 1
    asset = ASSET_ADDRESS
    transfered_amount = 1
    recipient = RECIPIENT_ADDRESS
    locksroot = LOCKSROOT

    msg = DirectTransfer(
        nonce,
        asset,
        transfered_amount,
        recipient,
        locksroot,
    )
    msg.sign(INITIATOR_PRIVKEY)
    packed = msg.packed()
    direct_transfer = str(packed.data)

    channel.closeSingleTransfer(direct_transfer)

    with pytest.raises(TransactionFailed):
        channel.closeSingleTransfer(direct_transfer, sender=tester.k2) # not participant

    assert channel.closed() == state.block.number
    assert channel.closingAddress() == tester.a0.encode('hex')
    # assert channel.participants(0)[10] == 1
    # assert channel.participants(0)[11] == token.address.encode('hex')
    # assert channel.participants(0)[9] == tester.a0.encode('hex')
    # assert channel.participants(0)[12] == tester.a1.encode('hex')
    # assert channel.participants(0)[3] == 1
    # assert channel.participants(0)[13] == LOCKSROOT
    # assert channel.participants(0)[7] == '\x00' * 32


def test_two_messages(state, token, channel):
    # test tokens and distribute tokens
    assert token.balanceOf(tester.a0) == 10000
    assert token.balanceOf(tester.a1) == 0
    assert token.transfer(tester.a1, 5000) is True
    assert token.balanceOf(tester.a0) == 5000
    assert token.balanceOf(tester.a1) == 5000

    # test global variables
    assert channel.settleTimeout() == 30
    assert channel.assetAddress() == token.address.encode('hex')
    assert channel.opened() == 0
    assert channel.closed() == 0
    assert channel.settled() == 0

    HASHLOCK1 = sha3(tester.k0)
    LOCK_AMOUNT1 = 29
    LOCK_EXPIRATION1 = 31
    LOCK1 = Lock(LOCK_AMOUNT1, LOCK_EXPIRATION1, HASHLOCK1)
    LOCKSROOT1 = merkleroot([
        sha3(LOCK1.as_bytes), ])   # print direct_transfer.encode('hex')

    nonce = 1
    asset = token.address
    transfered_amount = 1
    recipient = tester.a1
    locksroot = LOCKSROOT1

    msg1 = DirectTransfer(
        nonce,
        asset,
        transfered_amount,
        recipient,
        locksroot,
    )
    msg1.sign(tester.k0)
    packed = msg1.packed()
    direct_transfer1 = str(packed.data)

    HASHLOCK2 = sha3(tester.k1)
    LOCK_AMOUNT2 = 29
    LOCK_EXPIRATION2 = 31
    LOCK2 = Lock(LOCK_AMOUNT2, LOCK_EXPIRATION2, HASHLOCK2)
    LOCKSROOT2 = merkleroot([
        sha3(LOCK2.as_bytes), ])   # print direct_transfer.encode('hex')

    locksroot = LOCKSROOT2

    msg2 = DirectTransfer(
        2,  # nonce
        token.address,  # asset
        3,  # transfered_amount
        tester.a0,  # recipient
        locksroot,
    )
    msg2.sign(tester.k1)
    packed = msg2.packed()
    direct_transfer2 = str(packed.data)

    channel.close(direct_transfer1, direct_transfer2)

    with pytest.raises(TransactionFailed):
        # not participant
        channel.close(
            direct_transfer1,
            direct_transfer2,
            sender=tester.k2
        )

    # Test with message sender tester.a0
    assert channel.closed() == state.block.number
    assert channel.closingAddress() == tester.a0.encode('hex')
    # assert channel.participants(0)[10] == 1
    # assert channel.participants(0)[11] == token.address.encode('hex')
    # assert channel.participants(0)[9] == tester.a0.encode('hex')
    # assert channel.participants(0)[12] == tester.a1.encode('hex')
    # assert channel.participants(0)[3] == 1
    # assert channel.participants(0)[13] == LOCKSROOT1
    # assert channel.participants(0)[7] == '\x00' * 32

    # Test with message sender tester.a1
    assert channel.closed() == state.block.number
    assert channel.closingAddress() == tester.a0.encode('hex')
    # assert channel.participants(1)[10] == 2
    # assert channel.participants(1)[11] == token.address.encode('hex')
    # assert channel.participants(1)[9] == tester.a1.encode('hex')
    # assert channel.participants(1)[12] == tester.a0.encode('hex')
    # assert channel.participants(1)[3] == 3
    # assert channel.participants(1)[13] == LOCKSROOT2
    # assert channel.participants(1)[7] == '\x00' * 32


@pytest.mark.parametrize('asset_amount', [100])
def test_all_asset(asset_amount, state, channel, token):
    half_amount = asset_amount / 2
    assert token.transfer(tester.a1, half_amount) is True

    token1 = ABIContract(
        state,
        token.translator,
        token.address,
        default_key=tester.k1,
    )
    assert token.approve(channel.address, half_amount) is True
    assert token1.approve(channel.address, half_amount) is True

    channel1 = ABIContract(
        state,
        channel.translator,
        channel.address,
        default_key=tester.k1,
    )
    channel.deposit(half_amount)
    channel1.deposit(half_amount)

    _, deposit1, _, deposit2 = channel.addressAndBalance()

    assert deposit1 == half_amount
    assert deposit2 == half_amount

    assert token.balanceOf(channel.address) == asset_amount
    assert token.balanceOf(tester.a0) == 0
    assert token.balanceOf(tester.a1) == 0


def test_update_transfer(state, token, channel):
    # test tokens and distribute tokens
    assert token.balanceOf(tester.a0) == 10000
    assert token.balanceOf(tester.a1) == 0
    assert token.transfer(tester.a1, 5000) is True
    assert token.balanceOf(tester.a0) == 5000
    assert token.balanceOf(tester.a1) == 5000

    # test global variables
    assert channel.settleTimeout() == 30
    assert channel.assetAddress() == token.address.encode('hex')
    assert channel.opened() == 0
    assert channel.closed() == 0
    assert channel.settled() == 0

    HASHLOCK1 = sha3(tester.k0)
    LOCK_AMOUNT1 = 29
    LOCK_EXPIRATION1 = 31
    LOCK1 = Lock(LOCK_AMOUNT1, LOCK_EXPIRATION1, HASHLOCK1)
    LOCKSROOT1 = merkleroot([
        sha3(LOCK1.as_bytes),
    ])

    nonce = 1
    asset = token.address
    transfered_amount = 1
    recipient = tester.a1
    locksroot = LOCKSROOT1

    msg1 = DirectTransfer(
        nonce,
        asset,
        transfered_amount,
        recipient,
        locksroot,
    )
    msg1.sign(tester.k0)
    packed = msg1.packed()
    direct_transfer1 = str(packed.data)

    HASHLOCK2 = sha3(tester.k1)
    LOCK_AMOUNT2 = 29
    LOCK_EXPIRATION2 = 31
    LOCK2 = Lock(LOCK_AMOUNT2, LOCK_EXPIRATION2, HASHLOCK2)
    LOCKSROOT2 = merkleroot([
        sha3(LOCK2.as_bytes), ])   # print direct_transfer.encode('hex')

    locksroot = LOCKSROOT2

    msg2 = DirectTransfer(
        2,  # nonce
        token.address,  # asset
        3,  # transfered_amount
        tester.a0,  # recipient
        locksroot,
    )
    msg2.sign(tester.k1)
    packed = msg2.packed()
    direct_transfer2 = str(packed.data)

    # not yet closed
    with pytest.raises(TransactionFailed):
        channel.updateTransfer(direct_transfer1, sender=tester.k1)

    channel.close(direct_transfer1, direct_transfer2)

    # Test with message sender tester.a0
    assert channel.closed() == state.block.number
    assert channel.closingAddress() == tester.a0.encode('hex')
    # assert channel.participants(0)[10] == 1
    # assert channel.participants(0)[11] == token.address.encode('hex')
    # assert channel.participants(0)[9] == tester.a0.encode('hex')
    # assert channel.participants(0)[12] == tester.a1.encode('hex')
    # assert channel.participants(0)[3] == 1
    # assert channel.participants(0)[13] == LOCKSROOT1
    # assert channel.participants(0)[7] == '\x00' * 32

    # Test with message sender tester.a1
    assert channel.closed() == state.block.number
    assert channel.closingAddress() == tester.a0.encode('hex')
    # assert channel.participants(1)[10] == 2
    # assert channel.participants(1)[11] == token.address.encode('hex')
    # assert channel.participants(1)[9] == tester.a1.encode('hex')
    # assert channel.participants(1)[12] == tester.a0.encode('hex')
    # assert channel.participants(1)[3] == 3
    # assert channel.participants(1)[13] == LOCKSROOT2
    # assert channel.participants(1)[7] == '\x00' * 32

    HASHLOCK3 = sha3(tester.k1)
    LOCK_AMOUNT3 = 29
    LOCK_EXPIRATION3 = 31
    LOCK3 = Lock(LOCK_AMOUNT3, LOCK_EXPIRATION3, HASHLOCK3)
    LOCKSROOT3 = merkleroot([
        sha3(LOCK3.as_bytes), ])   # print direct_transfer.encode('hex')

    locksroot = LOCKSROOT3

    msg3 = DirectTransfer(
        3,  # nonce
        token.address,  # asset
        5,  # transfered_amount
        tester.a0,  # recipient
        locksroot,
    )
    msg3.sign(tester.k1)
    packed = msg3.packed()
    direct_transfer3 = str(packed.data)

    assert tester.DEFAULT_ACCOUNT == tester.a0
    tester.DEFAULT_ACCOUNT = tester.a1
    assert tester.DEFAULT_ACCOUNT == tester.a1
    # assert state.block.coinbase == tester.a1

    # closingAddress == getSender(message)
    with pytest.raises(TransactionFailed):
        channel.updateTransfer(direct_transfer1)

    channel.updateTransfer(direct_transfer3, sender=tester.k1)

    # Test with message sender tester.a1
    # assert channel.participants(1)[10] == 3
    # assert channel.participants(1)[11] == token.address.encode('hex')
    # assert channel.participants(1)[9] == tester.a1.encode('hex')
    # assert channel.participants(1)[12] == tester.a0.encode('hex')
    # assert channel.participants(1)[3] == 5
    # assert channel.participants(1)[13] == LOCKSROOT3
    # assert channel.participants(1)[7] == '\x00' * 32

    msg4 = DirectTransfer(
        1,  # nonce
        token.address,  # asset
        5,  # transfered_amount
        tester.a0,  # recipient
        locksroot,
    )
    msg4.sign(tester.k1)
    packed = msg4.packed()
    direct_transfer4 = str(packed.data)

    # nonce too low
    with pytest.raises(TransactionFailed):
        channel.updateTransfer(direct_transfer4, sender=tester.k1)

    # settleTimeout overdue
    state.block.number = 1158041

    with pytest.raises(TransactionFailed):
        channel.updateTransfer(direct_transfer3, sender=tester.k1)


def test_unlock(token, channel):
    HASHLOCK1 = sha3('x'*32)
    LOCK_AMOUNT1 = 29
    LOCK_EXPIRATION1 = 31
    LOCK1 = Lock(LOCK_AMOUNT1, LOCK_EXPIRATION1, HASHLOCK1)
    LOCKSROOT1 = merkleroot([
        sha3(LOCK1.as_bytes),
    ])

    nonce = 1
    asset = token.address
    transfered_amount = 1
    recipient = tester.a1
    locksroot = LOCKSROOT1

    msg1 = DirectTransfer(
        nonce,
        asset,
        transfered_amount,
        recipient,
        locksroot,
    )
    msg1.sign(tester.k0)
    packed = msg1.packed()
    direct_transfer1 = str(packed.data)

    HASHLOCK2 = sha3('x' * 32)
    LOCK_AMOUNT2 = 20
    LOCK_EXPIRATION2 = 31
    LOCK2 = Lock(LOCK_AMOUNT2, LOCK_EXPIRATION2, HASHLOCK2)
    LOCKSROOT2 = merkleroot([
        sha3(LOCK2.as_bytes), ])   # print direct_transfer.encode('hex')

    locksroot = LOCKSROOT2

    msg2 = DirectTransfer(
        2,  # nonce
        token.address,  # asset
        3,  # transfered_amount
        tester.a0,  # recipient
        locksroot,
    )
    msg2.sign(tester.k1)
    packed = msg2.packed()
    direct_transfer2 = str(packed.data)

    channel.close(direct_transfer1, direct_transfer2)

    HASHLOCK = sha3('x' * 32)
    LOCK_AMOUNT = 20
    LOCK_EXPIRATION = 31
    LOCK = Lock(LOCK_AMOUNT, LOCK_EXPIRATION, HASHLOCK)
    LOCKSROOT = merkleroot([
        sha3(LOCK.as_bytes),
    ])

    lock = str(LOCK.as_bytes)

    # TODO create correct test data
    channel.unlock(lock, LOCKSROOT, 'x' * 32)