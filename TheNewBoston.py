import os, sys
import asyncio
import discord
from discord.ext import commands
import requests
import django
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from nacl.encoding import HexEncoder
import nacl.signing
import json

import datetime, pytz
utc=pytz.UTC

import secrets

from functions import channelcheck, generate_block
from tasks import Giveaway

load_dotenv()
sys.path.append(os.getcwd() + '/API')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "API.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from main.models import User, Server, Transaction, Task

# ------------------------------------------------------------------------------------ Startup ------------------------------------------------------------------------------------


directory = os.getcwd()
file_directory = directory + "/files"

bot_prefix = os.environ.get('BOT_PREFIX')
token = os.environ.get('DISCORD_TOKEN')
manager_id = int(os.environ.get('MANAGER_ID'))
signing_key = nacl.signing.SigningKey(str.encode(os.environ.get('BOT_SIGNING_KEY')), encoder=nacl.encoding.HexEncoder)
bot_wallet = signing_key.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode('utf-8')

bot_color = 0xff0000

if None in [bot_prefix, signing_key, token, manager_id]:
    raise Exception("Please configure environment variables properly!")

intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix=bot_prefix, intents=intents)

class MyHelpCommand(commands.MinimalHelpCommand):
	async def send_pages(self):
		destination = self.get_destination()
		e = discord.Embed(color=bot_color, description='')
		desc = ''
		for command in [x for x in client.commands if not x.hidden]:
			if not command.brief == None:
				desc += f'\n**{command.name}** - {command.brief}'
		e.description = desc
		await destination.send(embed=e)

	async def send_command_help(self, command):
		destination = self.get_destination()
		e = discord.Embed(color=bot_color, description='')
		e.description = f'**{command.name}** - {command.description}'
		await destination.send(embed=e)
client.help_command = MyHelpCommand()


class Register:
	def __init__(self, user_id, address):
		self.user_id = user_id
		self.address = address

class Guild:
	def __init__(self, server_id, channel_id):
		self.server_id = server_id
		self.channel_id = channel_id
		self.main_channel = channel_id
		self.announcement_channel = channel_id

server_list = [] # servers with modified settings
address_holder = []

@client.event
async def on_ready():

	servers = await sync_to_async(Server.objects.all)()

	for server in servers:
		ServerObject = Guild(server.ServerID, server.ChannelID)
		if server.MainChannel != 0:
			ServerObject.main_channel = server.MainChannel

		if server.MainChannel != 0:
			ServerObject.announcement_channel = server.AnnouncementChannel

		server_list.append(ServerObject)

	print ("------------------------------------")
	print(f"Bot Name: {client.user.name}")
	print(f"Bot ID: {str(client.user.id)}")
	print(f"Discord Version: {discord.__version__}")
	print ("------------------------------------")
	await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="TNBC grow"))

# ------------------------------------------------------------------------------------ Constant ------------------------------------------------------------------------------------

async def constant():
	while True:
		await asyncio.sleep(3)
		r = requests.get(f"http://54.177.121.3/bank_transactions?format=json&limit=20&recipient={bot_wallet}") 
		info = r.json()
		deposits = await sync_to_async(Transaction.objects.filter)(Type="DEPOSIT")
		for tx in info["results"]:
			if tx["id"] not in [tx.TxID for tx in deposits]:
				try:
					user = await sync_to_async(User.objects.filter)(Address=tx['block']['sender'])
					await sync_to_async(user.update)(Coins=user[0].Coins+int(tx['amount']))
				except Exception as e:
					print(e)
				newTX = Transaction(Type="DEPOSIT", TxID=tx["id"], Amount=int(tx['amount']))
				newTX.save()

				try:
					user = await client.fetch_user(user[0].DiscordID)
					embed = discord.Embed(title="Success", description=f"Succesfully deposited {tx['amount']} coin(s) into your account", color=bot_color)
					await user.send(embed=embed)
				except Exception as e:
					print(e)
		tasks = await sync_to_async(Task.objects.all)()

		for task in tasks:
			if task.Date <= utc.localize(datetime.datetime.utcnow()):
				if task.Type == "GIVEAWAY":
					PassIn = json.loads(task.Info)
					await Giveaway(PassIn["host"], PassIn["message"], PassIn["guild"], PassIn["channel"], PassIn["amount"], server_list, client, bot_color)
					task.delete()


# ------------------------------------------------------------------------------------ User functions ------------------------------------------------------------------------------------

@client.command(pass_context=True, brief="Register address", description='Register your wallet address with the bot for future use.')
async def register(ctx, address=None):
	if await channelcheck(server_list, ctx):
		return

	async with ctx.channel.typing():

		if address == None:
			embed = discord.Embed(title="Register", description=f"To register your address, use the command `{bot_prefix}register [address]`. After this, you need to send 1 coin or more to `{bot_wallet}` and then using the command `{bot_prefix}verify` to confirm your address.", color=bot_color)
			await ctx.send(embed=embed)
		elif len(address) < 64:
			embed = discord.Embed(title="Invalid Address", description=f"Please enter a valid address!", color=bot_color)
			await ctx.send(embed=embed)
		else:
			users = await sync_to_async(User.objects.filter)(DiscordID=ctx.author.id)
			owned = await sync_to_async(User.objects.filter)(Address=address)
			other = False
			potential = None

			for pending in address_holder:
				if pending.user_id == ctx.author.id or pending.address == address:
					other = True
					potential = pending

			if any(users):
				embed = discord.Embed(title="Already Registered", description=f"You already have a registered address: `{users[0].Address}`", color=bot_color)
				await ctx.send(embed=embed)
				return
			elif other:
				if potential.user_id == ctx.author.id:
					address_holder.remove([x for x in address_holder if x.address == potential.address][0])
					address_holder.append(Register(ctx.author.id, address))
					embed = discord.Embed(title="Send a Coin!", description=f"Succesfully re-registered with new address. You now have to send 1 coin or more to `{bot_wallet}` from `{address}` and then use the command `{bot_prefix}verify` to confirm the address.", color=bot_color)
					await ctx.send(embed=embed)
					return
				embed = discord.Embed(title="In Use", description=f"Someone else is already registering this address", color=bot_color)
				await ctx.send(embed=embed)
				return
			elif any(owned):
				embed = discord.Embed(title="Already Owned", description=f"Someone else is already owns this address.", color=bot_color)
				await ctx.send(embed=embed)
				return
			else:
				address_holder.append(Register(ctx.author.id, address))
				embed = discord.Embed(title="Send a Coin!", description=f"You now have to send 1 coin or more to `{bot_wallet}` from `{address}` and then use the command `{bot_prefix}verify` to confirm the address.", color=bot_color)
				await ctx.send(embed=embed)


@client.command(pass_context=True, brief="Verify address", description='Verify your address to complete the registration process.')
async def verify(ctx):
	if await channelcheck(server_list, ctx):
		return


	async with ctx.channel.typing():

		for address in address_holder:
			if address.user_id == ctx.author.id:
				r = requests.get(f"http://54.177.121.3/bank_transactions?format=json&limit=1&block__sender={address.address}&recipient={bot_wallet}") # sender and receiver logic needed as well as a user DB
				info = r.json()
				if any(info["results"]):
					query = User(DiscordID=int(ctx.author.id), Address=address.address)
					query.save()
					newTX = Transaction(Type="DEPOSIT", TxID=info["results"][0]["id"], Amount=int(info["results"][0]['amount']))
					newTX.save()
					await ctx.send(f"Address `{address.address}` succesfully associated with {ctx.author.mention}")
					address_holder.remove(address)
				else:
					await ctx.send(f"No transaction detected from `{address.address}`")
				return
		embed = discord.Embed(title="No Address", description=f"No address to verify. Did you make sure to use `{bot_prefix}register [address]`?", color=bot_color)
		await ctx.send(embed=embed)

@client.command(pass_context=True, brief="View user status", description="View your or another registered user's status.")
async def status(ctx, member: discord.Member=None):
	if await channelcheck(server_list, ctx):
		return

	if not member:
		member = ctx.author


	async with ctx.channel.typing():
		records = await sync_to_async(User.objects.filter)(DiscordID=member.id)

		if any(records):
			user_address = records[0].Address
			user_coins = records[0].Coins

			r = requests.get(f"http://54.219.183.128/accounts/{user_address}/balance?format=json")
			info = r.json()

			amount = 0
			if any(info):
				amount = info["balance"]

			embed = discord.Embed(color=bot_color)
			embed.set_author(name=member.name, icon_url=member.avatar_url)
			embed.add_field(name='Address', value=user_address, inline=False)
			embed.add_field(name='Balance', value=amount)
			embed.add_field(name='Discord Account Balance', value=user_coins)
			await ctx.send(embed=embed)
		else:
			embed = discord.Embed(title="Unregistered", description=f"No address could be found for {member.name}", color=bot_color)
			embed.set_author(name=member.name, icon_url=member.avatar_url)
			await ctx.send(embed=embed)


@client.command(pass_context=True, brief="Earn coins", description='Learn about the ways to earn TNBC.')
async def earn(ctx):
	if await channelcheck(server_list, ctx):
		return

	embed = discord.Embed(title="Earn Coins", description="To earn coins, try completing some tasks: https://thenewboston.com/tasks/All", color=bot_color)
	await ctx.send(embed=embed)


@client.command(pass_context=True, brief="Deposit coins", description='Learn how to deposit coins to your Discord wallet.')
async def deposit(ctx):
	if await channelcheck(server_list, ctx):
		return

	embed = discord.Embed(title="Deposit", description=f"To deposit coins, simply make sure you are registered (`{bot_prefix}status`) and then send coins from your wallet to `{bot_wallet}`", color=bot_color)
	await ctx.send(embed=embed)


@client.command(pass_context=True, brief="Bot stats", description='View various statistics of the bot.')
async def stats(ctx):
	if await channelcheck(server_list, ctx):
		return

	async with ctx.channel.typing():

		r = requests.get(f"http://54.219.183.128/accounts/{bot_wallet}/balance?format=json")
		info = r.json()

		amount = info["balance"]

		embed = discord.Embed(title="Bot Stats", color=bot_color)
		embed.add_field(name='Servers', value=str(len(client.guilds)))
		embed.add_field(name='Users', value=str(len(await sync_to_async(User.objects.all)())))
		embed.add_field(name='Bot Balance', value=str(amount))
		await ctx.send(embed=embed)

@client.command(pass_context=True, brief="Show registered users", description='Shows the list of users on the server who are registered on the bot')
async def users(ctx):
	if await channelcheck(server_list, ctx):
		return

	async with ctx.channel.typing():

		users = (await sync_to_async(User.objects.filter)(DiscordID__in=[member.id for member in ctx.guild.members])).order_by('-Coins')

		userlist = ""
		addresslist = ""
		valuelist = ""

		for user in users:
			userlist += f"{ctx.guild.get_member(user.DiscordID).mention}\n"
			addresslist += f"{user.Address[:6]}...\n"
			valuelist += f"{user.Coins}\n"

		embed = discord.Embed(title="Registered Users", color=bot_color)
		embed.add_field(name='User', value=userlist)
		embed.add_field(name='Address', value=addresslist)
		embed.add_field(name='Account Value', value=valuelist)
		await ctx.send(embed=embed)

@client.command(pass_context=True, brief="Rain coins", description='Rain coins on the active and registered users of this server.')
async def rain(ctx, amount=None, people=None, timeout=30, limit=300):
	if await channelcheck(server_list, ctx):
		return

	ChannelID = ctx.channel.id
	for server in server_list:
		if server.server_id == ctx.guild.id:
			ChannelID = server.main_channel
			break

	channel = ctx.guild.get_channel(int(ChannelID))

	async with ctx.channel.typing():
		if amount == None or people == None:
			embed = discord.Embed(title="Missing Arguments", description=f"To rain, you need to do `{bot_prefix}rain [amount per person] [amount of people]`. ", color=bot_color)
			await ctx.send(embed=embed)
			return

		invalid = False

		try:
			amount = int(amount)
			people = int(people)
			timeout = int(timeout)*60
		except:
			invalid = True

		if amount <= 0 or people <= 1:
			invalid = True

		if invalid:
			embed = discord.Embed(title="Invalid Argument(s)", description="One or more of your passed arguments are invalid", color=bot_color)
			await ctx.send(embed=embed)
			return

		winners = []

		users = []


		def predicate(message):

			now = datetime.datetime.utcnow()
			delta = now - message.created_at
			return delta.total_seconds() <= timeout

		async for elem in channel.history(limit=limit).filter(predicate):
			if elem.author not in users and elem.author != ctx.author and not elem.author.bot:
				users.append(elem.author)

		author_records = await sync_to_async(User.objects.filter)(DiscordID=ctx.author.id)
		user_coins = 0

		if any(author_records):
			user_coins = author_records[0].Coins
			if user_coins >= amount*people:
				pass
			else:
				embed = discord.Embed(title="Not enough coins.", description=f"You only have {user_coins} out of {amount*people} coins in your wallet. You need to deposit coins to {bot_wallet} to rain.", color=bot_color)
				await ctx.send(embed=embed)
				return			
		else:
			embed = discord.Embed(title="Not registered.", description=f"You need to be registered to do a rain", color=bot_color)
			await ctx.send(embed=embed)
			return

		eligible = []

		for user in users:
			records = await sync_to_async(User.objects.filter)(DiscordID=user.id)

			if any(records):
				eligible.append(user)

		if len(eligible) < people:
			embed = discord.Embed(title="Not enough eligible.", description=f"This server only has {len(eligible)} eligible (registered and active) users out of your specified {people}", color=bot_color)
			await ctx.send(embed=embed)
			return

		for decision in range(people):

			potential_winner = secrets.choice(eligible)
			eligible.remove(potential_winner)
					

			records = await sync_to_async(User.objects.filter)(DiscordID=potential_winner.id)

			if any(records):
				winners.append(potential_winner)

		await sync_to_async(author_records.update)(Coins=author_records[0].Coins-(amount*people))

		winlist = ""
		for winner in winners:
			winlist += winner.mention + "\n"

			user = await sync_to_async(User.objects.filter)(DiscordID=winner.id)
			await sync_to_async(user.update)(Coins=user[0].Coins+amount)

		embed = discord.Embed(title=f"Rain by {ctx.author.name}!", color=bot_color)
		embed.add_field(name='Winners', value=winlist)
		embed.add_field(name='Amount', value=amount)
		await ctx.send(embed=embed)


@client.command(pass_context=True, brief="Start a timed giveaway", description="Create a timed giveaway of coins for one winner")
async def giveaway(ctx, amount=None, timeout=30):
	if await channelcheck(server_list, ctx):
		return


	async with ctx.channel.typing():
		if amount == None:
			embed = discord.Embed(title="Missing Arguments", description=f"To start a giveaway, you need to do `{bot_prefix}giveaway [amount] [time (in minutes)]`. ", color=bot_color)
			await ctx.send(embed=embed)
			return

		invalid = False

		try:
			amount = int(amount)
			timeout = int(timeout)
		except:
			invalid = True

		if amount <= 0 or timeout <= 1:
			invalid = True

		if invalid:
			embed = discord.Embed(title="Invalid Argument(s)", description="One or more of your passed arguments are invalid", color=bot_color)
			await ctx.send(embed=embed)
			return
		

		author_records = await sync_to_async(User.objects.filter)(DiscordID=ctx.author.id)
		user_coins = 0

		if any(author_records):
			user_coins = author_records[0].Coins
			if user_coins >= amount:
				pass
			else:
				embed = discord.Embed(title="Not enough coins.", description=f"You only have {user_coins} out of {amount} coins in your wallet. You need to deposit coins to {bot_wallet} to do a giveaway.", color=bot_color)
				await ctx.send(embed=embed)
				return			
		else:
			embed = discord.Embed(title="Not registered.", description=f"You need to be registered to do a giveaway", color=bot_color)
			await ctx.send(embed=embed)
			return

		await sync_to_async(author_records.update)(Coins=author_records[0].Coins-(amount))

		enddate = utc.localize(datetime.datetime.utcnow() + datetime.timedelta(minutes=timeout))

		announce = ctx.channel
		for server in server_list:
			if server.server_id == ctx.guild.id:
				announce = ctx.guild.get_channel(server.announcement_channel)

		embed = discord.Embed(title=f"Giveaway by {ctx.author.name}!", color=bot_color)
		embed.add_field(name='Ends', value=f"{enddate.strftime('%y-%m-%d %H:%M:%S')} GMT")
		embed.add_field(name='Amount', value=amount)
		message = await announce.send(embed=embed)

		await message.add_reaction("👍")

		info = {
		"host": ctx.author.id,
		"amount": amount,
		"guild": ctx.guild.id,
		"channel": announce.id,
		"message": message.id,
		}

		query = Task(Type="GIVEAWAY", Date=enddate, Info=json.dumps(info))
		query.save()


@client.command(pass_context=True, brief="Withdraw coins", description="Send coins from your Discord wallet to your registered wallet.")
async def withdraw(ctx, amount=None):
	if await channelcheck(server_list, ctx):
		return

	async with ctx.channel.typing():
		if amount == None:
			embed = discord.Embed(title="Missing Arguments", description=f"To withdraw, you need to do `{bot_prefix}withdraw [amount of coins excluding fee]`. ", color=bot_color)
			await ctx.send(embed=embed)
			return


		invalid = False
		records = await sync_to_async(User.objects.filter)(DiscordID=ctx.author.id)
		bank_config = requests.get('http://54.177.121.3/config?format=json').json()
		try:
			amount = int(amount)
		except:
			if amount == 'all':
				amount = records[0].Coins - (int(bank_config['default_transaction_fee'])+int(bank_config['primary_validator']['default_transaction_fee']))
			else:
				invalid = True

		if amount < 1:
			invalid = True

		if invalid:
			embed = discord.Embed(title="Invalid Argument(s)", description="One or more of your passed arguments are invalid", color=bot_color)
			await ctx.send(embed=embed)
			return


		if any(records):
			if records[0].Coins < amount + int(bank_config['default_transaction_fee'])+int(bank_config['primary_validator']['default_transaction_fee']):
				embed = discord.Embed(title="Inadequate Funds", description=f"You do not have enough coins in your discord wallet. \n Use `{bot_prefix}deposit` to add more coins. \n _Transaction fees may apply_", color=bot_color)
				embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
				await ctx.send(embed=embed)
			else:
				bank_config = requests.get('http://54.177.121.3/config?format=json').json()
				balance_lock = requests.get(f"{bank_config['primary_validator']['protocol']}://{bank_config['primary_validator']['ip_address']}:{bank_config['primary_validator']['port'] or 0}/accounts/{bot_wallet}/balance_lock?format=json").json()['balance_lock']
				txs = [
						{
							'amount': int(amount),
							'memo': f'Withdrawal for {ctx.author.name}',
							'recipient': records[0].Address
						},
						{
							'amount': int(bank_config['default_transaction_fee']),
							'fee': 'BANK',
							'recipient': bank_config['account_number'],
						},
						{
							'amount': int(bank_config['primary_validator']['default_transaction_fee']),
							'fee': 'PRIMARY_VALIDATOR',
							'recipient': bank_config['primary_validator']['account_number'],
						}
					]
				
				data = await generate_block(balance_lock, txs, signing_key)
				headers = {
					'Connection': 'keep-alive',
					'Accept': 'application/json, text/plain, */*',
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) TNBAccountManager/1.0.0-alpha.43 Chrome/83.0.4103.122 Electron/9.4.0 Safari/537.36',
					'Content-Type': 'application/json',
					'Accept-Language': 'en-US'
				}
				r = requests.request("POST", 'http://54.177.121.3/blocks', headers=headers, data=data)
				if r:
					if int(requests.get(f"http://54.219.183.128/accounts/{bot_wallet}/balance?format=json").json()['balance']) < amount+int(bank_config['primary_validator']['default_transaction_fee'])+int(bank_config['default_transaction_fee']):
						embed = discord.Embed(title="Error!", description=f"Please try again later.", color=bot_color)
						embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
						await ctx.send(embed=embed)
						return
					try:
						user = await sync_to_async(User.objects.filter)(Address=records[0].Address)
						await sync_to_async(user.update)(Coins=user[0].Coins-(amount+int(bank_config['primary_validator']['default_transaction_fee'])+int(bank_config['default_transaction_fee'])))
					except Exception as e:
						print(e)
					res = requests.get(f'http://54.177.121.3/bank_transactions?limit=1&recipient={records[0].Address}&amount={amount}').json()['results'][0]
					if r.json()['id'] == res['block']['id']:
						newTX = Transaction(Type="WITHDRAW", TxID=res["id"], Amount=int(res['amount']))
						newTX.save()

					embed = discord.Embed(title="Coins Withdrawn!", description=f"{amount} coins have been withdrawn to {records[0].Address} succesfully. \n Use `{bot_prefix}status` to check your new balance.", color=bot_color)
					embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
					await ctx.send(embed=embed)
				else:
					print(r.json())
					embed = discord.Embed(title="Error!", description=f"Please try again later.", color=bot_color)
					embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
					await ctx.send(embed=embed)
		else:
			embed = discord.Embed(title="Unregistered", description=f"No address could be found for {ctx.author.name}", color=bot_color)
			embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
			await ctx.send(embed=embed)



# ------------------------------------------------------------------------------------ Administrative ------------------------------------------------------------------------------------


@client.command(pass_context=True, hidden=True)
@commands.has_permissions(administrator=True)
async def kill(ctx):
	if int(ctx.author.id) == manager_id:
		await ctx.message.delete()
		await ctx.send("Recieved shutdown command, shutting down.")
		await asyncio.sleep(1)
		await client.close()
		sys.exit()
		exit()
	else:
		print("nah")

@client.command(pass_context=True, brief="kick member")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
	embed = discord.Embed(title="Member kicked.", description=f"Member kicked: {member.mention}\nReason: {reason}", color=bot_color)
	await ctx.message.delete()
	await ctx.send(embed=embed)
	await member.kick(reason=reason)

@client.command(pass_context=True, brief="ban member")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
	embed = discord.Embed(title="Member banned.", description=f"Member banned: {member.mention}\nReason: {reason}", color=bot_color)
	await ctx.message.delete()
	await ctx.send(embed=embed)
	await member.ban(reason=reason)

@client.command(pass_context=True, brief="clear messages")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=100):
	channel = ctx.message.channel
	messages = []
	async for message in channel.history(limit=amount):
		messages.append(message)
	await channel.delete_messages(messages)
	await ctx.send(f'{str(amount)} messages deleted.')

@client.command(pass_context=True, brief="Set commands channel")
@commands.has_permissions(administrator=True)
async def channel(ctx, channel: discord.TextChannel=None):
	if not channel:
		channel=ctx.channel
		
	query = Server(ServerID=int(ctx.guild.id), ChannelID=int(channel.id))
	query.save()
	server_list.append(Guild(int(ctx.guild.id), int(channel.id)))
	embed = discord.Embed(title="Settings changed", description=f"Commands channel set to: {channel.mention}", color=bot_color)
	await ctx.send(embed=embed)

@client.command(pass_context=True, brief="Set general channel")
@commands.has_permissions(administrator=True)
async def mainchannel(ctx, channel: discord.TextChannel=None):
	if not channel:
		channel=ctx.channel
		
	exists = False
	for pending in server_list:
		if pending.server_id == ctx.guild.id:
			pending.main_channel = channel.id
			exists = True

	if exists:
		query = await sync_to_async(Server.objects.filter)(ServerID=ctx.guild.id)
		await sync_to_async(query.update)(MainChannel=channel.id)

		embed = discord.Embed(title="Settings changed", description=f"general channel set to: {channel.mention}", color=bot_color)
		await ctx.send(embed=embed)
	else:
		embed = discord.Embed(title="No Commands Channel", description=f"You can only set a general channel if you have a normal commands channel set using `{bot_prefix}channel`", color=bot_color)
		await ctx.send(embed=embed)

@client.command(pass_context=True, brief="Set announcements channel")
@commands.has_permissions(administrator=True)
async def announcements(ctx, channel: discord.TextChannel=None):
	if not channel:
		channel=ctx.channel
		
	exists = False
	for pending in server_list:
		if pending.server_id == ctx.guild.id:
			pending.announcement_channel = channel.id
			exists = True

	if exists:
		query = await sync_to_async(Server.objects.filter)(ServerID=ctx.guild.id)
		await sync_to_async(query.update)(AnnouncementChannel=channel.id)

		embed = discord.Embed(title="Settings changed", description=f"Announcements channel set to: {channel.mention}", color=bot_color)
		await ctx.send(embed=embed)
	else:
		embed = discord.Embed(title="No Commands Channel", description=f"You can only set a announcement channel if you have a normal commands channel set using `{bot_prefix}channel`", color=bot_color)
		await ctx.send(embed=embed)

client.loop.create_task(constant())
client.run(token)
