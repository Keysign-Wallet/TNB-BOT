import os
import sys
import asyncio
import discord
from discord.voice_client import VoiceClient
from discord.ext import commands
import requests
import aiosqlite

# ------------------------------------------------------------------------------------ Startup ------------------------------------------------------------------------------------


directory = os.getcwd()
file_directory = directory + "/files"

client = commands.Bot(command_prefix='!')

token = open(file_directory + "/token.txt","r").read()

manager_id = 264475723283038208 # discord ID of the person managing the bot

bot_wallet = ""

db = None
c = None

class Register:
	def  __init__(self, user_id, address):
		self.user_id = user_id
		self.address = address


class Server:
	def __init__(self, server_id, channel_id):
		self.server_id = server_id
		self.channel_id = channel_id

server_list = [] # servers with modified settings
address_holder = []

@client.event
async def on_ready():

	global db
	global c

	db = await aiosqlite.connect(":memory:")
	c = await db.cursor()

	# remove once real DB has been created, this only needs to be created once. Preferably through command line.
	await c.execute("""CREATE TABLE servers (
			 server integer,
			 channel integer
			 )""")

	await c.execute("""CREATE TABLE users ( 
			 user integer,
			 address text
			 )""")
 	###
	await c.execute("SELECT * FROM servers")
	records = await c.fetchall()

	await db.commit()

	for row in records:
		server_list.append(Server(row[0], row[1]))

	print ("------------------------------------")
	print(f"Bot Name: {client.user.name}")
	print(f"Bot ID: {str(client.user.id)}")
	print(f"Discord Version: {discord.__version__}")
	print ("------------------------------------")
	await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="TNBC grow"))

# ------------------------------------------------------------------------------------ User functions ------------------------------------------------------------------------------------

@client.command(pass_context=True, description="Register address")
async def register(ctx, address=None):
	if address == None:
		await ctx.send(f"To register your address, use the command ´!register [address]´. After this, you have 15 minutes to send coins to `{bot_wallet}` and then using the command `!verify` to confirm your address.")
	else:
		await c.execute(f"SELECT * FROM users WHERE user={ctx.author.id}")
		records = await c.fetchall()
		if any(records):
			await ctx.send(f"You already have a registered address: `{records[1]}`")
			return
		else:
			address_holder.append(Register(ctx.author.id, address))
			await ctx.send(f"You now have 15 minutes to send coins to `{bot_wallet}` from `{address}` and then use the command `!verify` to confirm the address.")


@client.command(pass_context=True, description="Verify transaction")
async def verify(ctx):
	for address in address_holder:
		if address.user_id == ctx.author.id:
			r = requests.get(f"http://54.193.31.159/bank_transactions?format=json&limit=1&block__sender={address.address}&recipient={bot_wallet}") # sender and receiver logic needed as well as a user DB
			info = r.json()
			if any(info["results"]):
				await c.execute(f"INSERT INTO users VALUES ({int(ctx.author.id)}, {address.address})")
				await ctx.send(f"Address `{address.address}` succesfully associated with {ctx.author.mention}")
				address_holder.remove(address)
			else:
				await ctx.send(f"No transaction detected from `{address.address}`")
			return
	await ctx.send("No address to verify. Did you make sure to use `!register [address]`?")

@client.command(pass_context=True, description="Check the verification status of a user")
async def Status(ctx, member: discord.Member):
	await c.execute(f"SELECT * FROM users WHERE user={member.id}")
	records = await c.fetchall()
	if any(records):
		await ctx.send(f"{member.name} has a verified address at ´{records[1]}´")
	else:
		await ctx.send(f"No address could be found for {member.name}")


# ------------------------------------------------------------------------------------ Administrative ------------------------------------------------------------------------------------


@client.command(pass_context=True, description="secret")
async def kill(ctx):
	if int(ctx.author.id) == manager_id:
		await ctx.message.delete()
		await ctx.send("Recieved shutdown command, shutting down.")
		await asyncio.sleep(1)
		await client.close()
		await db.close()
		sys.exit()
		exit()
	else:
		print("nah")

@client.command(pass_context=True, description="kick member")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
	embed = discord.Embed(title="Member kicked.", description=f"Member kicked: {member.mention}\nReason: {reason}", color=0xff0000)
	await ctx.message.delete()
	message = await ctx.send(embed=embed)
	await member.kick(reason=reason)

@client.command(pass_context=True, description="ban member")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
	embed = discord.Embed(title="Member banned.", description=f"Member banned: {member.mention}\nReason: {reason}", color=0xff0000)
	await ctx.message.delete()
	message = await ctx.send(embed=embed)
	await member.ban(reason=reason)

@client.command(pass_context=True, description="clear messages") # in case of a raid
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=100):
	channel = ctx.message.channel
	messages = []
	async for message in channel.history(limit=amount):
		messages.append(message)
	await channel.delete_messages(messages)
	await ctx.send(f'{str(amount)} messages deleted.')

@client.command(pass_context=True, description="Set commands channel")
@commands.has_permissions(administrator=True)
async def channel(ctx, channel: discord.TextChannel):
	await c.execute(f"INSERT INTO servers VALUES ({int(ctx.guild.id)}, {int(channel.id)})")
	server_list.append(Server(int(ctx.guild.id), int(channel.id)))
	embed = discord.Embed(title="Settings changed", description=f"Commands channel set to: {channel.mention}", color=0xff0000)
	message = await ctx.send(embed=embed)

client.run(token)