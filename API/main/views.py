from django.core import serializers
from django.http import HttpResponse, JsonResponse
from .models import User
from django.forms.models import model_to_dict

# Create your views here.
def users(request):
	address = None
	userid = None
	address = request.GET.get('address')
	userid = request.GET.get('userid')
	users = User.objects.all()
	if userid:
		users = users.filter(DiscordID=userid)
	if address:
		users = users.filter(address=address)
	results = [{'DiscordID': x.DiscordID, 'Address': x.Address, 'Coins': x.Coins} for x in users]
	return JsonResponse({'results': results})