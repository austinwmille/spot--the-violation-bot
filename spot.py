import discord
from discord.ext import commands, tasks
import os
import sys
import subprocess
import random
import asyncio
import time
from functools import wraps
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process  # if you plan to use fuzzy matching
from functools import wraps


# Load tokens securely
load_dotenv("botsecs.env")
TOKEN = os.getenv("DISCORD_TOKEN")  # Ensure DISCORD_TOKEN is set in botsecs.env
spoid = os.getenv("spoid")
spoecs = os.getenv("spoecs")
gptkey = os.getenv("gptkey")

guildID = 1140053353615859842
musicchannelID = 1140053354240815157

# Set up Discord intents and bot
intents = discord.Intents.default()
intents.message_content = True  # Enable in Developer Portal
bot = commands.Bot(command_prefix="!", intents=intents)

# Set up Spotify authentication
sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=spoid,
    client_secret=spoecs,
    redirect_uri="http://localhost:8888/callback",
    scope="user-modify-playback-state user-read-playback-state user-read-currently-playing"
))

# Replace with allowed Discord user IDs
ALLOWED_USER_IDS = [
    688148738774138913,
    472099505269899266,
    #764260458898915345,
    699750640993173522
]

def allowed_users_only(func):
    @wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        if ctx.author.id in ALLOWED_USER_IDS:
            return await func(ctx, *args, **kwargs)
        else:
            await ctx.send("Your taste in music has been deemed not shitty enough to use this command, uWu")
    return wrapper

# Check required environment variables
required_env_vars = ["DISCORD_TOKEN", "spoid", "spoecs", "gptkey"]
for var in required_env_vars:
    if not os.getenv(var):
        print(f"Missing environment variable: {var}")
        exit(1)

@tasks.loop(seconds=15)
async def update_spotify_status():
    try:
        current_track = sp.current_playback()
        if current_track and current_track.get('is_playing'):
            # Extract only the artist name from the first artist.
            artist_name = current_track['item']['artists'][0]['name']
            status = f"{artist_name}"
        else:
            status = "..."
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
    except Exception as e:
        print(f"Error updating Spotify status: {e}")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Spotify Bot"))

# OpenAI client setup
client = OpenAI(api_key=gptkey)

@tasks.loop(seconds=5)
async def auto_stream():
    try:
        current_playback = sp.current_playback()
    except Exception as e:
        print(f"Error fetching Spotify playback: {e}")
        current_playback = None

    # If Spotify is playing
    if current_playback and current_playback.get('is_playing'):
        # Determine if the bot is already in a voice channel for the desired guild
        guild = bot.get_guild(guildID)
        # Check if the bot has an active voice client in this guild
        voice_client = discord.utils.get(bot.voice_clients, guild=guild)
        
        # If not connected, try to join
        if not voice_client:
            channel = guild.get_channel(musicchannelID)
            if channel and isinstance(channel, discord.VoiceChannel):
                try:
                    voice_client = await channel.connect()
                except Exception as e:
                    print(f"Could not connect to voice channel: {e}")
                    return
        
        # If connected but not already playing audio, start playing
        if voice_client and not voice_client.is_playing():
            try:
                # Prepare FFmpegPCMAudio source from the virtual cable
                source = discord.FFmpegPCMAudio(
                    source="audio=CABLE Output (VB-Audio Virtual Cable)",
                    before_options="-f dshow -analyzeduration 0 -probesize 32",
                    options="-ac 2 -ar 48000 -bufsize 256k -threads 2 -vn"
                )
                voice_client.play(source, after=lambda e: print(f"Playback finished: {e}"))
            except Exception as e:
                print(f"Error starting audio stream: {e}")
    else:
        # If Spotify is not playing and the bot is connected, disconnect to be unobtrusive
        for vc in bot.voice_clients:
            try:
                await vc.disconnect()
                print("Leaving channel because music stopped")
            except Exception as e:
                print(f"Error disconnecting voice client: {e}")

@bot.event
async def on_ready():
    auto_stream.start()
    update_spotify_status.start()  # This updates the status with the artist name

@bot.event
async def on_message(message):
    # Skip processing messages from bots.
    if message.author.bot:
        return

    content = message.content.strip()
    # Check if the message begins with "spot" (case-insensitive)
    if content.lower().startswith("spot"):
        # Remove "spot" from the beginning and trim whitespace.
        input_text = content[len("spot"):].strip()
        # Rewrite the message content to include the command prefix and command name.
        # For instance, if a user types:
        #    spot how are you?
        # It becomes:
        #    !spot how are you?
        message.content = f"!spot {input_text}"
    await bot.process_commands(message)

@bot.command()
@allowed_users_only
async def quit_close(ctx):
    """Shut down the bot."""
    await ctx.send("night, sempai")
    await bot.close()

@bot.command()
async def guild_info(ctx):
    """Sends a summary of the guild’s member count, roles, and channels."""
    guild = ctx.guild
    member_count = guild.member_count
    roles = ", ".join([role.name for role in guild.roles if role.name != "@everyone"])
    channels = ", ".join([channel.name for channel in guild.channels])
    info = (
        f"**Guild Name:** {guild.name}\n"
        f"**Member Count:** {member_count}\n"
        f"**Roles:** {roles}\n"
        f"**Channels:** {channels}"
    )
    await ctx.send(info)


# ---------------- Spotify Output Setup ----------------

# these functions have been superceded by the auto_play function

# ---------------- Status Tasks ----------------
@bot.command()
async def show_emojis(ctx):
    emojis = [str(emoji) for emoji in ctx.guild.emojis]
    await ctx.send(f"Available emojis: {' '.join(emojis)}")

@bot.command()
@allowed_users_only
async def restart(ctx):
    await ctx.send("Restarting the bot...")
    # Flush the stdout so messages get out before restart.
    sys.stdout.flush()
    os.execl(sys.executable, sys.executable, *sys.argv)

# ---------------- Spotify Control Commands ----------------

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def currentsong(ctx):
    try:
        current_track = sp.current_playback()
        if current_track and current_track['is_playing']:
            track_name = current_track['item']['name']
            artist_name = current_track['item']['artists'][0]['name']
            await ctx.send(f"🎵 Currently playing: *{track_name}* by {artist_name}")
        else:
            await ctx.send("No music is currently playing, uWu.")
    except Exception as e:
        print(f"Error fetching current song: {e}")
        await ctx.send("Something went wrong while fetching the current song.")

@bot.command()
@allowed_users_only
async def play(ctx, *, song_name):
    results = sp.search(q=song_name, type="track", limit=5)
    if results['tracks']['items']:
        track_uri = results['tracks']['items'][0]['uri']
        sp.start_playback(uris=[track_uri])
        await ctx.send(f"Now playing: {results['tracks']['items'][0]['name']}")
    else:
        await ctx.send("Song not found. Try a different search term.")

@bot.command()
@allowed_users_only
async def pause_unpause(ctx):
    """Pause/resume Spotify playback."""
    try:
        # Note: Using Spotify API directly since voice_client may not control playback.
        current = sp.current_playback()
        if current and current['is_playing']:
            sp.pause_playback()
            await ctx.send("Music paused, uWu.")
        else:
            sp.start_playback()
            await ctx.send("Resumed playback, uWu.")
    except Exception as e:
        print(f"Error during playback: {e}")
        await ctx.send(f"Error controlling playback: {e}")

@bot.command()
@allowed_users_only
async def skip(ctx):
    try:
        sp.next_track()
        await ctx.send("Skipped current track, uWu.")
    except Exception as e:
        print(f"Error skipping track: {e}")
        await ctx.send("Error skipping track. Is something playing?")

@bot.command()
async def volume(ctx, level: int):
    if 0 <= level <= 100:
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.source.volume = level / 100
            await ctx.send(f"Volume set to {level}%.")
        else:
            await ctx.send("No audio is currently playing.")
    else:
        await ctx.send("Please specify a volume between 0 and 100.")

# ---------------- GPT Integration Command ----------------

# Global dictionary to store conversation context per user:
user_contexts = {}
MAX_CONTEXT_LENGTH = 10  # Maximum conversation turns to keep

def get_guild_summary(ctx):
    guild = ctx.guild
    members = guild.member_count
    roles = ", ".join([role.name for role in guild.roles if role.name != "@everyone"])
    return f"The guild is named '{guild.name}' and has {members} members with the following roles: {roles}."

@bot.command(name="spot")
async def spot(ctx, *, input_text: str):
    """
    Uses GPT to interpret the user's natural language input with some memory of previous exchanges.
    Handles both commands and conversational queries.
    """
    # Generate a guild summary
    guild_context = get_guild_summary(ctx)
    # User-specific information
    user_context = f"The current user is {ctx.author.name} (ID: {ctx.author.id})."
    
    # Retrieve or initialize context for this user, starting with a system prompt.
    context = user_contexts.get(ctx.author.id, [
        {"role": "system", "content": (
            f"You are an interpreter for a Discord bot whose main functionality is Spotify playback. "
            f"In addition, you have the following context: {guild_context} {user_context} "
            f"The bot supports the following commands: {get_commands_list_text()}. "
            "When the user's input clearly maps to one of these commands, reply with 'COMMAND: spot<command> <arguments>' exactly. "
            "If the message is conversational or vague, reply with 'CHAT: <your response>' and help the user accordingly."
        )}
    ])
    
    # Append the current user input to the context.
    context.append({"role": "user", "content": input_text})
    
    # Limit context length
    if len(context) > MAX_CONTEXT_LENGTH:
        context = context[-MAX_CONTEXT_LENGTH:]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # Or your model of choice
            messages=context
        )
        result = response.choices[0].message.content.strip()
        print("GPT response:", result)
    except Exception as e:
        await ctx.send(f"Error processing your request: {e}")
        return

    # Append the GPT response to the context and update stored memory.
    context.append({"role": "assistant", "content": result})
    user_contexts[ctx.author.id] = context

    if result.startswith("COMMAND:"):
        command_text = result.replace("COMMAND:", "").strip()
        if not command_text.startswith("spot"):
            command_text = "spot" + command_text
        await ctx.send("Running command")
        new_message = ctx.message
        new_message.content = command_text  # For example, "spot currentsong"
        cmd_name = new_message.content.split()[0].lstrip("spot")
        if bot.get_command(cmd_name) is None:
            await ctx.send(f"Error: the command '{cmd_name}' is not recognized. Please try again.")
        else:
            await bot.process_commands(new_message)
    elif result.startswith("CHAT:"):
        chat_reply = result.replace("CHAT:", "").strip()
        await ctx.send(chat_reply)
    else:
        await ctx.send("Sorry, I can't decide if you wanted a response or a command.")

def get_commands_list_text():
    command_names = [cmd.name for cmd in bot.commands]
    return ", ".join(f"!{name}" for name in command_names)

# ---------------- Spotify Queue Commands ----------------

from collections import deque
song_queue = deque()

# ---------------- Basic Utility Commands ----------------

@bot.command()
async def weather(ctx, *, city: str):
    response = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid=your_api_key")
    data = response.json()
    if data.get("cod") != "404":
        main_data = data["main"]
        weather_desc = data["weather"][0]["description"]
        await ctx.send(f"Weather in {city}: {weather_desc}, {main_data['temp']}K")
    else:
        await ctx.send("City not found.")

@bot.command()
async def joke(ctx):
    response = requests.get("https://official-joke-api.appspot.com/random_joke")
    joke = response.json()
    await ctx.send(f"{joke['setup']} - {joke['punchline']}")

@bot.command()
async def fact(ctx):
    response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en")
    fact = response.json()
    await ctx.send(f"Did you know? {fact['text']}")

# ---------------- Interaction with Other Discord Bots ----------------

@bot.command()
async def quote(ctx, message_id: int):
    try:
        message = await ctx.fetch_message(message_id)
        await ctx.send(f"Quote: {message.content}")
    except discord.NotFound:
        await ctx.send("Message not found.")

# ---------------- Enhanced Music Features ----------------

@bot.command()
async def queue(ctx, *, song_name):
    results = sp.search(q=song_name, type="track", limit=1)
    if results['tracks']['items']:
        song_uri = results['tracks']['items'][0]['uri']
        song_queue.append(song_uri)
        await ctx.send(f"Added {results['tracks']['items'][0]['name']} to the queue.")
    else:
        await ctx.send("Song not found.")

@bot.command()
async def skip_all(ctx):
    song_queue.clear()
    await ctx.send("Cleared the queue!")

# ---------------- Games and Fun Commands ----------------

@bot.command()
async def flip(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"The coin landed on: {result}")

@bot.command()
async def roll(ctx, sides: int):
    result = random.randint(1, sides)
    await ctx.send(f"You rolled a {result} on a {sides}-sided dice.")

# ---------------- Integration with Other Services ----------------

@bot.command()
async def news(ctx):
    response = requests.get("https://newsapi.org/v2/top-headlines?country=us&apiKey=your_api_key")
    data = response.json()
    if data["status"] == "ok":
        articles = data["articles"]
        news = "\n".join([f"{article['title']} - {article['url']}" for article in articles[:5]])
        await ctx.send(f"Latest News:\n{news}")
    else:
        await ctx.send("Couldn't fetch the news.")

# ---------------- Admin Commands ----------------


# ---------------- User Interaction Commands ----------------

@bot.command()
async def remind(ctx, time: int, *, reminder: str):
    await ctx.send(f"Reminder set! I will remind you in {time} seconds.")
    await asyncio.sleep(time)
    await ctx.send(f"Reminder: {reminder}")

# ---------------- Custom Responses and Fun Interactions ----------------

@bot.command()
async def greet(ctx, name: str):
    await ctx.send(f"Hello, {name}! How are you today?")


# Run the bot
bot.run(TOKEN)
