import discord
from discord.ext import commands, tasks
import os
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
    #764260458898915345
]

def allowed_users_only(func):
    @wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        if ctx.author.id in [688148738774138913, 472099505269899266]:
            return await func(ctx, *args, **kwargs)
        else:
            await ctx.send("Your taste in music has not been deemed shitty enough to use this command, uWu")
    return wrapper

# Check required environment variables
required_env_vars = ["DISCORD_TOKEN", "spoid", "spoecs", "gptkey"]
for var in required_env_vars:
    if not os.getenv(var):
        print(f"Missing environment variable: {var}")
        exit(1)

# OpenAI client setup
client = OpenAI(api_key=gptkey)

# ------------------ Command Handling ------------------

# List of valid bot commands
VALID_COMMANDS = [
    "violateme", "joinmesempai", "violatemesempai", "hitmesempai",
    "skipthissempai", "sleepsempai", "play", "currentsong",
    "volume", "show_emojis", "summon", "ping", "nightsempai", "hey"
]

@bot.event
async def on_message(message):
    # Ignore messages from the bot and non-commands
    if message.author == bot.user or not message.content.startswith("!"):
        return

    user_input = message.content[1:].strip()  # Remove the leading "!"
    command_name = user_input.split()[0]
    if command_name in VALID_COMMANDS:
        await bot.process_commands(message)
        return

    # Otherwise, use OpenAI to determine the intended command.
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": (
                "You are a Discord bot that helps users by converting their input into valid bot commands. "
                "Only return one command from this list:\n"
                "!violateme, !joinmesempai, !violatemesempai, !hitmesempai, "
                "!skipthissempai, !sleepsempai, !play, !currentsong, "
                "!volume, !show_emojis, !summon, !ping, !nightsempai, !hey\n"
                "If no command fits, return 'UNKNOWN_COMMAND'."
            )},
            {"role": "user", "content": f"User input: `{user_input}`. What command should be used?"}
        ]
    )
    ai_suggestion = response.choices[0].message.content.strip()
    if ai_suggestion in VALID_COMMANDS:
        message.content = ai_suggestion  # Replace with AI suggestion
        await message.channel.send(f"🤖 **Did you mean:** `{ai_suggestion}`?")
        await bot.process_commands(message)
    else:
        await message.channel.send("❌ **Unknown command.** Try `!help` for a list of commands.")

@bot.event
async def on_ready():
    print("Registered Commands:", [cmd.name for cmd in bot.commands])
    print(f"{bot.user} is online!")

# ---------------- Spotify Output Setup ----------------

def set_spotify_output():
    """Runs a PowerShell script to set Spotify output device."""
    try:
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "C:\\Users\\austi\\GitHub\\spot--the-violation-bot\\switchitup.ps1"], check=True)
        print("Spotify output changed to CABLE Input successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to change Spotify output: {e}")

# Call the function at startup
set_spotify_output()

import atexit
def reset_spotify_output():
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "./switchitup.ps1", "stop"])
atexit.register(reset_spotify_output)

# ---------------- Status Tasks ----------------

@tasks.loop(seconds=30)
async def cycle_status():
    statuses = [
        discord.Activity(type=discord.ActivityType.playing, name="with Spotify"),
        discord.Activity(type=discord.ActivityType.listening, name="your commands"),
        discord.Activity(type=discord.ActivityType.watching, name="over the server"),
        discord.Activity(type=discord.ActivityType.playing, name="!help for commands"),
    ]
    new_status = random.choice(statuses)
    await bot.change_presence(activity=new_status)

@tasks.loop(seconds=15)
async def update_spotify_status():
    try:
        current_track = sp.current_playback()
        if current_track and current_track['is_playing']:
            track_name = current_track['item']['name']
            artist_name = current_track['item']['artists'][0]['name']
            status = f"🎵 {track_name} by {artist_name}"
        else:
            status = "silence 🎧"
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
    except Exception as e:
        print(f"Error updating Spotify status: {e}")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Spotify Bot"))

@bot.command()
async def show_emojis(ctx):
    emojis = [str(emoji) for emoji in ctx.guild.emojis]
    await ctx.send(f"Available emojis: {' '.join(emojis)}")

# ---------------- Lyrics & Genius Commands ----------------

def search_genius_lyrics(song_name, artist_name):
    search_url = "https://www.austinmiller.net/search"
    headers = {"Authorization": f"Bearer YOUR_GENIUS_API_KEY"}  # Replace with your Genius API key
    params = {"q": f"{song_name} {artist_name}"}
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["response"]["hits"]:
            return data["response"]["hits"][0]["result"]["url"]
    return None

def fetch_lyrics_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        lyrics_div = soup.find("div", class_="lyrics")
        if lyrics_div:
            return lyrics_div.get_text()
    return None

@bot.command(name="lyrics")
async def lyrics(ctx):
    try:
        current_track = sp.current_playback()
        if current_track and current_track['is_playing']:
            track_name = current_track['item']['name']
            artist_name = current_track['item']['artists'][0]['name']
            lyrics_url = search_genius_lyrics(track_name, artist_name)
            if lyrics_url:
                await ctx.send(f"🎵 **Lyrics for *{track_name}* by {artist_name}:**\n{lyrics_url}")
            else:
                await ctx.send("❌ Lyrics not found for this song.")
        else:
            await ctx.send("❌ No song is currently playing.")
    except Exception as e:
        print(f"Error fetching lyrics: {e}")
        await ctx.send("❌ Something went wrong while fetching lyrics.")

@bot.command()
async def realtime_lyrics(ctx):
    try:
        current_track = sp.current_playback()
        if current_track and current_track['is_playing']:
            track_name = current_track['item']['name']
            artist_name = current_track['item']['artists'][0]['name']
            lrc_file = f"{track_name}_{artist_name}.lrc"  # Ensure you have a matching LRC file
            await display_lyrics(ctx, lrc_file)
        else:
            await ctx.send("No song is currently playing.")
    except Exception as e:
        print(f"Error displaying lyrics: {e}")
        await ctx.send("Something went wrong while displaying lyrics.")

def parse_lrc(lrc_file):
    lyrics = []
    with open(lrc_file, "r") as file:
        for line in file:
            if line.startswith("["):
                time_tag = line.split("]")[0][1:]
                lyric = line.split("]")[1].strip()
                lyrics.append((time_tag, lyric))
    return lyrics

async def display_lyrics(ctx, lrc_file):
    lyrics = parse_lrc(lrc_file)
    for time_tag, lyric in lyrics:
        minutes, seconds = time_tag.split(":")
        seconds = float(minutes) * 60 + float(seconds)
        await asyncio.sleep(seconds)
        await ctx.send(lyric)

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
async def hitmesempai(ctx):
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
async def skipthissempai(ctx):
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

# ---------------- Voice Channel Commands ----------------

@bot.command(aliases=['join', 'connect'])
@allowed_users_only
async def joinmesempai(ctx):
    """Join the user's voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("Joined the voice channel, ready to violate.")
    else:
        await ctx.send("You're not in a voice channel, dummy.")

@bot.command()
@allowed_users_only
async def violatemesempai(ctx):
    """Stream audio from a virtual audio cable."""
    if ctx.voice_client:
        vc = ctx.voice_client
        try:
            print("Attempting Spotify violation...")
            source = discord.FFmpegPCMAudio(
                source="audio=CABLE Output (VB-Audio Virtual Cable)",
                before_options="-f dshow -analyzeduration 0 -probesize 32",
                options="-ac 2 -ar 48000 -bufsize 256k -threads 2 -vn"
            )
            vc.play(source, after=lambda e: print(f"Playback finished: {e}"))
            await ctx.send("Illegal activities have commenced! Enjoy.")
        except Exception as e:
            print(f"Error during playback: {e}")
            await ctx.send(f"Error playing audio: {e}")
    else:
        await ctx.send("Bring me to the voice channel first, uWu.")

@bot.command()
@allowed_users_only
async def sleepsempai(ctx):
    """Leave the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Legality reestablished.")
    else:
        await ctx.send("I'm not in a voice channel, uWu.")

@bot.command()
async def summon(ctx):
    await ctx.send("I'm here and ready to violate copyright, uWu!")

@bot.command()
async def violateme(ctx):
    """Sends a random violation message."""
    responses = [
        "you're a dirty girl.",
        "get on your knees and throat me.",
        "yeah, you like that don't you.",
        "Be careful with that language..",
        "violated in 4K.",
        "congrats, you're now on a watchlist.",
        "your FBI agent is deeply concerned.",
        "this is why we can't have nice things.",
        "do you ever just sit and think about your choices?",
        "damn, even I wasn't ready for that one.",
        "that's an HR violation waiting to happen."
    ]
    await ctx.send(random.choice(responses))

@bot.command()
@allowed_users_only
async def shutdown(ctx):
    """Shut down the bot and reset Spotify output."""
    await ctx.send("Goodbye, uWu!")
    switchitup("stop")
    await bot.close()

@bot.command()
async def nightsempai(ctx):
    """Shut down the bot."""
    await ctx.send("Goodbye, uWu!")
    await bot.close()

# ---------------- GPT Integration Command ----------------

# For context persistence across calls, use a global dictionary.
user_contexts = {}

@commands.cooldown(1, 4, commands.BucketType.user)
@bot.command()
async def hey(ctx, *, question: str):
    MAX_CONTEXT_LENGTH = 10  # Keep last 10 messages per user
    user_id = ctx.author.id
    if user_id not in user_contexts:
        user_contexts[user_id] = [{"role": "system", "content": "You are a Discord bot assistant with subtle anti-capitalist and existential undertones. Be nice but slightly indifferent."}]
    user_contexts[user_id].append({"role": "user", "content": question})
    if len(user_contexts[user_id]) > MAX_CONTEXT_LENGTH:
        user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT_LENGTH:]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=user_contexts[user_id]
    )
    answer = response.choices[0].message.content.strip()
    await ctx.send(answer)

# ---------------- Spotify Queue Commands ----------------

from collections import deque
song_queue = deque()

@bot.command()
async def queue(ctx, *, song_name):
    results = sp.search(q=song_name, type="track", limit=1)
    if results['tracks']['items']:
        song_queue.append(results['tracks']['items'][0]['uri'])
        await ctx.send(f"Added to queue: {results['tracks']['items'][0]['name']}")
    else:
        await ctx.send("Song not found.")

# ---------------- Signal Handling ----------------

import signal
import sys
def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    switchitup("stop")
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def switchitup(action):
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "C:\\Users\\austi\\GitHub\\spot--the-violation-bot\\switchitup.ps1", action])

@bot.event
async def on_disconnect():
    switchitup("stop")
    print("Bot stopped, Spotify output switched back to Default.")

# ---------------- Test Example (if needed) ----------------

# You might remove or separate tests from production code.
"""
import pytest
from discord.ext.commands import Bot, Context

@pytest.mark.asyncio
async def test_ping_command():
    bot = Bot(command_prefix="!")
    ctx = Context(message=..., bot=bot)
    await bot.get_command('ping').callback(ctx)
    assert ctx.channel.last_message.content == "heard."
"""

# Run the bot
bot.run(TOKEN)
