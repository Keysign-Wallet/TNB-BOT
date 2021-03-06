import asyncio
from nacl.encoding import HexEncoder
from operator import itemgetter
import json

async def generate_block(balance_lock, transactions, signing_key):
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



async def channelcheck(server_list, ctx):
	if ctx.author.guild_permissions.administrator:
		return False

	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return True
                
	return False