import os
import sys
import asyncio
import discord
from discord.voice_client import VoiceClient
from discord.ext import commands
import requests
from django.conf import settings
import django
from asgiref.sync import sync_to_async
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.getcwd() + '/API')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "API.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from main.models import User, Server

# ------------------------------------------------------------------------------------ Startup ------------------------------------------------------------------------------------


directory = os.getcwd()
file_directory = directory + "/files"

bot_prefix = os.environ.get('BOT_PREFIX')
token = os.environ.get('DISCORD_TOKEN')
manager_id = int(os.environ.get('MANAGER_ID'))
bot_wallet = os.environ.get('BOT_WALLET')
if None in [bot_prefix, bot_wallet, token, manager_id]:
    raise Exception("Please configure environment variables properly!")

client = commands.Bot(command_prefix=bot_prefix)


class Register:
	def  __init__(self, user_id, address):
		self.user_id = user_id
		self.address = address


class Guild:
	def __init__(self, server_id, channel_id):
		self.server_id = server_id
		self.channel_id = channel_id

server_list = [] # servers with modified settings
address_holder = []

@client.event
async def on_ready():

	servers = await sync_to_async(Server.objects.all)()

	for server in servers:
		server_list.append(Guild(server.ServerID, server.ChannelID))

	print ("------------------------------------")
	print(f"Bot Name: {client.user.name}")
	print(f"Bot ID: {str(client.user.id)}")
	print(f"Discord Version: {discord.__version__}")
	print ("------------------------------------")
	await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="TNBC grow"))

# ------------------------------------------------------------------------------------ User functions ------------------------------------------------------------------------------------

@client.command(pass_context=True, brief="Register address")
async def register(ctx, address=None):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return

	if address == None:
		await ctx.send(f"To register your address, use the command `>register [address]`. After this, you need to send 1 coin or more to `{bot_wallet}` and then using the command `>verify` to confirm your address.")
	elif len(address) < 64:
		await ctx.send("Please enter a valid address!")
	else:
		users = await sync_to_async(User.objects.filter)(DiscordID=ctx.author.id)
		owned = await sync_to_async(User.objects.filter)(Address=address)
		other = False
		potential = None

		for pending in address_holder:
			if pending.address == address:
				other = True
				potential = pending

		if any(users):
			await ctx.send(f"You already have a registered address: `{users[0].Address}`")
			return
		elif other:
			if potential.user_id == ctx.author.id:
				address_holder.remove(potential)
				address_holder.append(Register(ctx.author.id, address))
				await ctx.send(f"Succesfully re-registered with new address. You now have to send 1 coin or more to `{bot_wallet}` from `{address}` and then use the command `>verify` to confirm the address.")
				return
			await ctx.send(f"Someone else is already registering this address")
			return
		elif any(owned):
			await ctx.send(f"Someone else is already owns this address.")
			return
		else:
			address_holder.append(Register(ctx.author.id, address))
			await ctx.send(f"You now have to send 1 coin or more to `{bot_wallet}` from `{address}` and then use the command `>verify` to confirm the address.")


@client.command(pass_context=True, brief="Verify address registration transaction")
async def verify(ctx):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return
	for address in address_holder:
		if address.user_id == ctx.author.id:
			r = requests.get(f"http://13.57.215.62/bank_transactions?format=json&limit=1&block__sender={address.address}&recipient={bot_wallet}") # sender and receiver logic needed as well as a user DB
			info = r.json()
			if any(info["results"]):
				query = User(DiscordID=int(ctx.author.id), Address=address.address)
				query.save()
				await ctx.send(f"Address `{address.address}` succesfully associated with {ctx.author.mention}")
				address_holder.remove(address)
			else:
				await ctx.send(f"No transaction detected from `{address.address}`")
			return
	await ctx.send("No address to verify. Did you make sure to use `>register [address]`?")

@client.command(pass_context=True, brief="Check the verification status of a user")
async def status(ctx, member: discord.Member=None):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return

	if not member:
		member = ctx.author
	records = await sync_to_async(User.objects.filter)(DiscordID=member.id)
	if any(records):
		await ctx.send(f"{member.name} has a verified address at `{records[0].Address}`")
	else:
		await ctx.send(f"No address could be found for {member.name}")

@client.command(pass_context=True, brief="Ways to earn coins")
async def earn(ctx):
	for server in server_list:
		if server.server_id == ctx.guild.id:
			if ctx.channel.id != server.channel_id:
				return

	await ctx.send("To earn coins, try completing some tasks: https://thenewboston.com/tasks/All")
# ------------------------------------------------------------------------------------ Administrative ------------------------------------------------------------------------------------


@client.command(pass_context=True, brief="secret")
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
	embed = discord.Embed(title="Member kicked.", description=f"Member kicked: {member.mention}\nReason: {reason}", color=0xff0000)
	await ctx.message.delete()
	message = await ctx.send(embed=embed)
	await member.kick(reason=reason)

@client.command(pass_context=True, brief="ban member")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
	embed = discord.Embed(title="Member banned.", description=f"Member banned: {member.mention}\nReason: {reason}", color=0xff0000)
	await ctx.message.delete()
	message = await ctx.send(embed=embed)
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
async def channel(ctx, channel: discord.TextChannel):
	query = Server(ServerID=int(ctx.guild.id), ChannelID=int(channel.id))
	server_list.append(Guild(int(ctx.guild.id), int(channel.id)))
	embed = discord.Embed(title="Settings changed", description=f"Commands channel set to: {channel.mention}", color=0xff0000)
	message = await ctx.send(embed=embed)

client.run(token)