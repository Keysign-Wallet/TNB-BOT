from django.db import models

# Create your models here.
class User(models.Model):
	DiscordID = models.IntegerField()
	Address = models.TextField()

	def __str__(self):
		return str(self.DiscordID)

class Server(models.Model):
	ServerID = models.IntegerField()
	ChannelID = models.IntegerField()

	def __str__(self):
		return str(self.ServerID)