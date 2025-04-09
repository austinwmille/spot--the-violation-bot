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
    #764260458898915345
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
                    print("Oh! There's music playing")
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
                print("Started streaming Spotify output.")
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

@bot.command()
@allowed_users_only
async def nightsempai(ctx):
    """Shut down the bot."""
    await ctx.send("night, sempai")
    await bot.close()

# ------------------ Command Handling ------------------

# List of valid bot commands
VALID_COMMANDS = [
    "hitmesempai",
    "skipthissempai", "sleepsempai", "play", "currentsong",
    "volume", "show_emojis", "nightsempai"
]

# ---------------- Spotify Output Setup ----------------

# these functions have been superceded by the auto_play function

# ---------------- Status Tasks ----------------
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

# ---------------- GPT Integration Command ----------------

# For context persistence across calls, use a global dictionary.
user_contexts = {}

@commands.cooldown(1, 4, commands.BucketType.user)
@bot.command(name="spot")
async def spot(ctx, *, input_text: str):
    """
    Interprets the user's natural language input to either trigger a command or provide a conversational reply.
    """
    # Define a system prompt that instructs ChatGPT to decide between command or conversation.
    system_prompt = (
        "You are an interpreter for a Discord Spotify bot. The bot supports the following commands: "
        "!play <song>, !currentsong, !hitmesempai, !skipthissempai, !queue <song>, !lyrics. "
        "When the user input clearly maps to one of these commands, reply with 'COMMAND: ' followed by the exact command. "
        "If the user is simply having a conversation or asking a general question, reply with 'CHAT: ' followed by the response."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text}
            ]
        )
        # Get the result from ChatGPT.
        result = response.choices[0].message.content.strip()
    except Exception as e:
        await ctx.send(f"Error processing your request: {e}")
        return

    # Check if the result indicates a command or a general chat reply.
    if result.startswith("COMMAND:"):
        # Extract the command portion.
        command_text = result.replace("COMMAND:", "").strip()
        await ctx.send(f"Running command")
        # Option A: Re-dispatch the message as if the user typed a bot command.
        new_message = ctx.message
        new_message.content = command_text  # Should be something like "!play song_name"
        await bot.process_commands(new_message)
        
        # Option B (alternative): Directly map and call the function for the command.
        # For example, if command_text.startswith("!play"), you can call:
        #   await play(ctx, song_name=command_text.split(" ", 1)[1])
    elif result.startswith("CHAT:"):
        chat_reply = result.replace("CHAT:", "").strip()
        await ctx.send(chat_reply)
    else:
        # Fallback if the response doesn't have the expected prefixes.
        await ctx.send("Sorry, did you want me to run a command or just give a response?")


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

# Run the bot
bot.run(TOKEN)
