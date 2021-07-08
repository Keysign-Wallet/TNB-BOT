# TNB-BOT

TNBC Discord bot (outdated source)

Add the bot https://discord.com/api/oauth2/authorize?client_id=823155121197416458&permissions=8&scope=bot

### Setting up the bot

A basic bot to create asscossiation between wallet addresses and discord users. This way people can find each others' real and trusted address on a platform where they know they are talking to the correct person.

# Installation for developers and contributors

## Python

Install python 3.9 to your computer, and make sure to include the "add to path" option during installation, as well as the "pip" package option

## Discord Bot Creation

1. Log in to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create your testing bot by pressing "New Application" at the top right, then naming your app
3. In the new application, go to the "Bot" section
4. Press "Add Bot" and then confirm the creation
5. In the new "Bot" section, note the "token" as you will need to copy it for later
6. Enable "server members intent"
7. Go to "OAuth2" and select the "bot" scope to generate an invite link to your bot
8. Invite your bot to whatever discord server you would like to test the bot on.

## Bot

1. Download the latest version from the main branch
2. Head into the folder holding "thenewboston.py" using a terminal
3. Install the requirements using pip:

```
pip install -r requirements.txt
```

4. Copy the `example.env` file to a new file called `.env` and replace the values with the preferred ones.
5. The token copied earlier, in the step 5 of "Discord Bot Creation" should be the value of `DISCORD_TOKEN`
6. Run "python thenewboston.py" in the terminal (Will not work well until the API is set up, as you have no DB yet)

## API

1. Open a terminal in the `API` folder'
2. Run `python manage.py makemigrations` and `python manage.py migrate` to generate your database
3. Run `python manage.py createsuperuser` to create an admin login to your API so you can manage your database easily
4. Run `python manage.py runserver` (And you can optionally add a space after it and then `0.0.0.0:PORT` to specify a port)
5. Head to `127.0.0.1:PORT/API/users` to see if the users' info shows up

To manually manage the database, head to `127.0.0.1:PORT/admin` and log in, then go to the "Users" model under "MAIN"

This was written without any double-checking or testing, but should work. If there are any issues, feel free to open an issue and we will try to resolve it ASAP.
