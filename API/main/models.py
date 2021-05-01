from django.db import models

# Create your models here.
class User(models.Model):
	DiscordID = models.IntegerField()
	Address = models.TextField()
	Coins = models.IntegerField(default=0)

	def __str__(self):
		return str(self.DiscordID)

class Server(models.Model):
	ServerID = models.IntegerField()
	ChannelID = models.IntegerField()
	MainChannel = models.IntegerField(default=0)
	AnnouncementChannel = models.IntegerField(default=0)

	def __str__(self):
		return str(self.ServerID)

class Transaction(models.Model):
	Type = models.TextField()
	TxID = models.TextField()
	Amount = models.IntegerField()

	def __str__(self):
		return str(self.TxID)

class Task(models.Model):
	Type = models.TextField()
	Info = models.TextField()
	Date = models.DateTimeField()

	def __str__(self):
		return str(self.Type)