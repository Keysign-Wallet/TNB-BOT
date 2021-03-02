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

client = commands.Bot(command_prefix='!', intents=intents)

token = open(file_directory + "/token.txt","r").read()

manager_id = 264475723283038208 # discord ID of the person managing the bot



db = None
c = None



class Server:
	def __init__(self, server_id, channel_id):
		self.server_id = server_id
		self.channel_id = channel_id


server_list = [] # servers with modified settings

@client.event
async def on_ready():

	global db
	global c

	db = await aiosqlite.connect(":memory:")
	c = await db.cursor()

	await c.execute("""CREATE TABLE servers ( # remove once real DB has been created, this only needs to be created once. Preferably through command line.
			 server integer,
			 channel integer
			 )""")

	await c.execute("SELECT * FROM servers")
	records = await c.fetchall()

	await db.commit()

	for row in records:
		server_list.append(Server(records[row][0], records[row][1]))

	print ("------------------------------------")
	print(f"Bot Name: {client.user.name}")
	print(f"Bot ID: {str(client.user.id)}")
	print(f"Discord Version: {discord.__version__}")
	print ("------------------------------------")
	await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="TNBC grow"))



# ------------------------------------------------------------------------------------ loops ------------------------------------------------------------------------------------

"""
async def transactions():
	await asyncio.sleep(10)
	guild = client.get_guild(528965652938096653)
	channel = guild.get_channel(ongoing.channel)
	while True:
		r = requests.get("http://54.193.31.159/bank_transactions?format=json&limit=1")
		info = r.json()
		if 
			date_object = datetime.strptime(date_string, "%d %B, %Y")
"""
# ------------------------------------------------------------------------------------ Administrative ------------------------------------------------------------------------------------

@client.command(pass_context=True, description="secret")
async def kill(ctx):
	if ctx.author.id == manager_id:
		await ctx.message.delete()
		await ctx.send("Recieved shutdown command, shutting down.")
		await asyncio.sleep(1)
		await client.close()
		sys.exit()

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
async def channel(ctx, channel: discord.Channel):
	await c.execute(f"INSERT INTO servers VALUES ({int(ctx.guild.id)}, {int(channel.id)})")
	server_list.append(Server(int(ctx.guild.id), int(channel.id)))
	embed = discord.Embed(title="Settings changed", description=f"Commands channel set to: {channel.mention}", color=0xff0000)
	message = await ctx.send(embed=embed)

#client.loop.create_task(transactions())
client.run(token)