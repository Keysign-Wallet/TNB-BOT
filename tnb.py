from operator import itemgetter
import json

def generate_block(balance_lock, transactions, signing_key):
    account_number = signing_key.verify_key.encode(encoder=HexEncoder).decode('utf-8')
    message = {
        'balance_key': balance_lock,
        'txs': sorted(transactions, key=itemgetter('recipient'))
    }
    signature = signing_key.sign(json.dumps(message, separators=(',', ':'), sort_keys=True).encode('utf-8')).signature.hex()
    block = {
        'account_number': account_number,
        'message': message,
        'signature': signature
    }
    return json.dumps(block)