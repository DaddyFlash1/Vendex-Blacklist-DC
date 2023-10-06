import logging
import discord
from discord.ext import commands
import os.path
import re
import asyncio
import aiohttp
import os
import json
from datetime import datetime, timedelta

# Define your bot token and prefix
TOKEN = 'MTEyODY5NjI3ODc4ODg2NjEwOA.GvOHPl.IwaSyc-245LyeSZcf3B6YnrUKVD8dtoc9x0t54'
PREFIX = '!'

# Define the number of consecutive uppercase characters that trigger anti-CAPSLOCK
CAPSLOCK_THRESHOLD = 5

# Define the number of consecutive similar messages that trigger anti-spam
SPAM_THRESHOLD = 3

# Define your webhook URL for logging
WEBHOOK_URL = 'https://discord.com/api/webhooks/1128696106495246408/pgkb2HGO-YHcRy97WqLKW79CqT1LWYwY1dV2_K_pfsEkyISGKFM7sWSpo78vv60XEiz4'

# Define the path to the blacklist file
BLACKLIST_PATH = 'idblack.js'
idblack_PATH = 'idblack.txt'
idblack_PATH = 'idblack.js'
FXban_Path = 'FXban.js'
BANLOGS_PATH = 'banlogs.js'

# Define the rate limit duration (in seconds)
RATE_LIMIT_DURATION = 80
# Define the maximum number of requests allowed within the rate limit duration
RATE_LIMIT_MAX_REQUESTS = 7

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if the FXban.js file exists
if not os.path.isfile(FXban_Path):
    print(f"Error: FXban.js file not found in the specified path: {FXban_Path}")
    exit(1)

# Check if the banlogs.js file exists
if not os.path.isfile(BANLOGS_PATH):
    print(f"Error: banlogs.js file not found in the specified path: {BANLOGS_PATH}")
    exit(1)

# Keep track of the webhook rate limit
webhook_rate_limit = {}
webhook_rate_limit_lock = asyncio.Lock()


# Create an instance of the bot with intents
intents = discord.Intents.all()
intents.messages = True  # Enable messages intent
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Command cooldowns
bot.cooldown_mapping = commands.CooldownMapping.from_cooldown(
    1, 10, commands.BucketType.user
)

# Event for when the bot is ready
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="FX Security"))


# Event for processing messages
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check for links and delete the message
    if contains_link(message.content):
        await message.delete()
        await message.channel.send(f'{message.author.mention}, posting links is not allowed.')
        await log_to_webhook(message.author, f'Posted links: {message.content}', message.channel.id)
        await asyncio.sleep(5)  # Add a delay of 5 seconds
        await message.channel.purge(limit=1)  # Delete the bot's message

    # Check for excessive CAPSLOCK usage
    if is_capslock(message.content):
        await message.delete()
        await message.channel.send(f'{message.author.mention}, please avoid excessive CAPSLOCK usage.')
        await log_to_webhook(message.author, f'Excessive CAPSLOCK usage: {message.content}', message.channel.id)
        await asyncio.sleep(5)  # Add a delay of 5 seconds
        await message.channel.purge(limit=1)  # Delete the bot's message

    # Check for spam
    if is_spam(message):
        await message.delete()
        await message.channel.send(f'{message.author.mention}, please refrain from spamming.')
        await log_to_webhook(message.author, f'Spam detected: {message.content}', message.channel.id)
        await asyncio.sleep(5)  # Add a delay of 5 seconds
        await message.channel.purge(limit=1)  # Delete the bot's message

    # Check if the user's ID is blacklisted
    if is_blacklisted(message.author.id):
        await asyncio.sleep(10)  # Add a delay of 10 seconds
        member = message.guild.get_member(message.author.id)
        if member:
            await member.kick(reason='Blacklisted ID')
            await log_to_webhook(member, f'User kicked for having a blacklisted ID: {member.id}', message.channel.id)

    # Process commands as usual for non-administrator users
    await bot.process_commands(message)


# Event for logging channel messages
@bot.event
async def on_message_delete(message):
    # Log deleted messages
    await log_to_webhook(message.author, f'Deleted message: {message.content}', message.channel.id)


# Read blacklisted IDs from idblack.txt file
def read_blacklist():
    with open(BLACKLIST_PATH, 'r') as file:
        return file.read().splitlines()


# Read ban logs from banlogs.js file
def read_banlogs():
    with open(BANLOGS_PATH, 'r') as file:
        return json.load(file)


# Write ban logs to banlogs.js file
def write_banlogs(banlogs):
    with open(BANLOGS_PATH, 'w') as file:
        json.dump(banlogs, file)


# Event triggered when a member joins the server
@bot.event
async def on_member_join(member):
    # Check if the member's ID is in the blacklist
    if str(member.id) in read_blacklist():
        await asyncio.sleep(10)  # Wait for 10 seconds
        await member.kick(reason='Blacklisted')
        print(f'Kicked {member.name}#{member.discriminator} ({member.id})')


# Command to add a user to the whitelist
@bot.command()
@commands.has_permissions(administrator=True)
async def whitelist(ctx, member: discord.Member):
    # Add the user to the whitelist
    # Implement your own whitelist logic here, such as storing in a database or file
    # For example: whitelist.add(member.id)
    await ctx.send(f'{member.display_name} has been whitelisted.')
    await log_to_webhook(ctx.author, f'Whitelisted user: {member.display_name}', ctx.channel.id)


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if the user has administrator permissions
    if message.author.guild_permissions.administator:
        # Allow administrators to bypass all checks and commands
        await bot.process_commands(message)
        return


# Command to unban all members
@bot.command()
@commands.has_permissions(administrator=True)
async def unban_all(ctx):
    banned_users = await ctx.guild.bans()

    for banned_entry in banned_users:
        member_id = banned_entry.user.id
        try:
            await ctx.guild.unban(discord.Object(id=member_id))
            await log_to_webhook(ctx.author, f'Unbanned user with ID: {member_id}', ctx.channel.id)
        except discord.NotFound:
            pass

    await ctx.send('All members have been unbanned.')


# Command to kick a user
@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    # Kick the user from the server
    await member.kick(reason=reason)

    # Log the kick event
    await log_to_webhook(ctx.author, f'Kicked user: {member.display_name}', ctx.channel.id)

    await ctx.send(f'{member.display_name} has been kicked.')


# Command to ban a user
@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member):
    # Ban the user from the server
    await ctx.guild.ban(member)

    # Store the ban in the ban log
    banlogs = read_banlogs()
    banlogs[str(member.id)] = {
        'name': str(member),
        'reason': 'No reason provided'  # You can modify this to include a reason for the ban
    }
    write_banlogs(banlogs)

    await log_to_webhook(ctx.author, f'Banned user: {member.display_name}', ctx.channel.id)

    await ctx.send(f'{member.display_name} has been banned.')


# Command to stop the bot
@bot.command()
@commands.is_owner()
async def stop(ctx):
    await ctx.send('Stopping the bot...')
    await log_to_webhook(ctx.author, 'Stopping the bot...', ctx.channel.id)
    await bot.close()


# Purge command to delete messages
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, limit: int):
    await ctx.channel.purge(limit=limit + 1)
    await ctx.send(f'Successfully deleted {limit} messages.', delete_after=5)
    await log_to_webhook(ctx.author, f'Successfully deleted {limit} messages.', ctx.channel.id)


# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f'This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.')
        await log_to_webhook(ctx.author, f'Command on cooldown: {ctx.message.content}', ctx.channel.id)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Please provide all the required arguments for the command.')
        await log_to_webhook(ctx.author, f'Missing required arguments: {ctx.message.content}', ctx.channel.id)
    else:
        await ctx.send('An error occurred while processing the command.')
        await log_to_webhook(ctx.author, f'Command error: {error}', ctx.channel.id)


# Function to check if a message contains a link
def contains_link(content):
    # Use regular expression to match URLs starting with https:// or http://
    regex = r"(https?://\S+)"
    matches = re.findall(regex, content)
    return bool(matches)


# Function to check if a message contains excessive CAPSLOCK usage
def is_capslock(content):
    consecutive_uppercase = 0
    for char in content:
        if char.isupper():
            consecutive_uppercase += 1
            if consecutive_uppercase >= CAPSLOCK_THRESHOLD:
                return True
        else:
            consecutive_uppercase = 0
    return False


# Function to check if a message is considered spam
def is_spam(message):
    # Implement your own spam detection logic here
    # You can use message.content, message.author, etc. to determine if a message is spam
    # For example, you can check if the user has sent similar messages in a short period of time
    # You can use a database or cache to store message history and timestamps
    return False


@bot.event
async def on_message_edit(before, after):
    # Log edited messages
    await log_to_webhook(before.author, f'Edited message: {before.content} -> {after.content}', before.channel.id)


# Function to log events to a webhook with rate limiting
async def log_to_webhook(author, content, channel_id):
    # Check the rate limit for the current channel
    async with webhook_rate_limit_lock:
        now = datetime.now()
        if channel_id not in webhook_rate_limit:
            # If the channel is not in the rate limit dictionary, create a new entry
            webhook_rate_limit[channel_id] = {
                'timestamp': now,
                'requests': 1
            }
        else:
            # If the channel is in the rate limit dictionary, check if the rate limit has been reached
            rate_limit_info = webhook_rate_limit[channel_id]
            if now - rate_limit_info['timestamp'] > timedelta(seconds=RATE_LIMIT_DURATION):
                # If the duration has passed, reset the rate limit for the channel
                rate_limit_info['timestamp'] = now
                rate_limit_info['requests'] = 1
            else:
                # If the duration has not passed, check if the maximum requests limit has been reached
                if rate_limit_info['requests'] >= RATE_LIMIT_MAX_REQUESTS:
                    # If the limit has been reached, return without sending the log
                    return
                else:
                    # If the limit has not been reached, increment the requests count
                    rate_limit_info['requests'] += 1

    # Check if the content contains an IP address and delete the message if found
    if contains_ip(content):
        return

    avatar_url = author.avatar.url if author.avatar else author.default_avatar.url
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
        await webhook.send(content, username=author.name, avatar_url=avatar_url,
                           allowed_mentions=discord.AllowedMentions.none(),
                           files=[], embeds=[], tts=False)


# Function to check if a message contains an IP address
def contains_ip(content):
    # Use regular expression to match IP addresses
    regex = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    matches = re.findall(regex, content)
    return bool(matches)


# Function to check if a user's ID is blacklisted
def is_blacklisted(id):
    # Implement your own logic to check if the ID is blacklisted
    # Read the blacklist from the file and compare the ID
    # For example, you can read the blacklist.js file and compare the ID against the list of blacklisted IDs
    with open(BLACKLIST_PATH, 'r') as file:
        blacklist = file.read().splitlines()
    return str(id) in blacklist


# Import your custom ban log and whitelist modules
# Replace "FXban" and "Cbans" with the appropriate modules/files for ban log and whitelist storage
# Modify the imports based on your implementation

# Note: Ensure that the module files exist in the specified paths
# and the import statements are correct.

# Run the bot
bot.run(TOKEN)
