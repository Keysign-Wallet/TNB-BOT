import asyncio
from asgiref.sync import sync_to_async
import secrets
import discord
import datetime
import sys, os

import django

sys.path.append(os.getcwd() + '/API')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "API.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from main.models import User

async def Giveaway(host, message, guild, channel, amount, server_list, client, bot_color):

	guild = client.get_guild(guild)
	channel = guild.get_channel(channel)
	message = await channel.fetch_message(message)

	participants = await message.reactions[0].users().flatten()
	
	participants = [person.id for person in participants]

	eligible = []

	for user in participants:
		if user != host and user != client.user.id:
			records = await sync_to_async(User.objects.filter)(DiscordID=user)

			if any(records):
				eligible.append(user)

	winner = secrets.choice(eligible)


	host = user = await client.fetch_user(host)
	user = await client.fetch_user(winner)


	announce = channel
	for server in server_list:
		if server.server_id == guild.id:
			announce = guild.get_channel(server.announcement_channel)

	records = await sync_to_async(User.objects.filter)(DiscordID=winner)
	await sync_to_async(records.update)(Coins=records[0].Coins+(amount))


	embed = discord.Embed(title=f"Giveaway by {host.name}!", color=bot_color)
	embed.add_field(name='Ended', value=f"{datetime.datetime.utcnow().strftime('%y-%m-%d %H:%M:%S')} GMT")
	embed.add_field(name='Amount', value=amount)
	embed.set_footer(text=f"Giveaway won by {user.name}")
	await message.edit(embed=embed)

	embed = discord.Embed(title="Congratulations!", description=f"You have won {amount} coins in a giveaway by {host}", color=bot_color)
	await user.send(embed=embed)

	embed = discord.Embed(title=f"Giveaway has ended!", color=bot_color)
	embed.add_field(name='Host', value=host.mention)
	embed.add_field(name='Winner', value=user.mention)
	embed.add_field(name='Amount', value=amount)
	await announce.send(embed=embed)

	