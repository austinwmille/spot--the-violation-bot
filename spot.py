import discord
from discord.ext import commands
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv  # For secure token handling
import subprocess
import random
import asyncio
from functools import wraps


# Load tokens securely
load_dotenv("botsecs.env")
TOKEN = os.getenv("DISCORD_TOKEN")  # Make sure to set DISCORD_TOKEN in your .env file
spoid = os.getenv("spoid")
spoecs = os.getenv("spoecs")

# Set up intents and bot
intents = discord.Intents.default()
intents.message_content = True  # Ensure this is enabled in the Developer Portal
bot = commands.Bot(command_prefix="!", intents=intents)

# set up spotify auths
sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=spoid,
    client_secret=spoecs,
    redirect_uri="http://localhost:8888/callback",
    scope="user-modify-playback-state user-read-playback-state user-read-currently-playing"
))

# Replace with the Discord user IDs of allowed users
ALLOWED_USER_IDS = [688148738774138913, 472099505269899266]  # Add your ID and the other user's ID

@bot.event
async def on_ready():
    switchitup("start")
    print(f"{bot.user} has connected to Discord and Spotify output switched to CABLE Input!")
    
    while True:
        try:
            current_track = sp.current_playback()
            if current_track and current_track['is_playing']:
                track_name = current_track['item']['name']
                artist_name = current_track['item']['artists'][0]['name']
                status = f"🎵 {track_name} by {artist_name}"
            else:
                status = "silence 🎧"
            await bot.change_presence(activity=discord.Game(name=status))
        except Exception as e:
            print(f"Error updating status: {e}")
            await bot.change_presence(activity=discord.Game(name="Spotify Bot"))
        await asyncio.sleep(15)

# Decorator to restrict commands to allowed users
def allowed_users_only(func):
    @wraps(func)  # Preserve the original function name
    async def wrapper(ctx, *args, **kwargs):
        if ctx.author.id in ALLOWED_USER_IDS:
            return await func(ctx, *args, **kwargs)
        else:
            await ctx.send("your taste in music has not been deemed shitty enough to use this command, uWu")
    return wrapper

@bot.command()
async def helpmestepbro(ctx):
    """Display a list of available commands and their descriptions."""
    help_message = """
**Spot, the Violation Bot** - Commands:
    
- `!joinmesempai`: Joins your current voice channel.
- `!violatemesempai`: Starts streaming Spotify audio through the bot.
- `!hitmesempai`: Pause/resume Spotify playback.
- `!skipthissempai`: Skip the currently playing track.
- `!sleepsempai`: Makes the bot leave the voice channel.
- `!currentsong`: Display the currently playing Spotify song. (WIP)
- `!volume <0-100>`: Set the volume for the bot. (WIP)
- `!recommendsong`: Suggest a random song from your playlists.
- `!violateme`: Get a random (very) dirty response from the bot.
- `!helpmestepbro`: Show this help message.

*Bask in my ~~cum~~--glory, uWu*
"""
    await ctx.send(help_message)


@bot.command()
@allowed_users_only
async def hitmesempai(ctx):
    """Pause/resume Spotify playback."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("music theft has been paused.")
    elif ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("copyright infringement reestablished, uWu.")
    else:
        await ctx.send("bruh. do you hear anything??")

#@bot.event
#async def on_ready():
#    statuses = [
#        "violating Spotify TOS",
#        "playing illegal tunes",
#        "streaming fire tracks",
#    ]
#    while True:
#        await bot.change_presence(activity=discord.Game(name=random.choice(statuses)))
#        await asyncio.sleep(30)  # Change status every 30 seconds

@bot.command()
@allowed_users_only
async def skipthissempai(ctx):
    """Skip the current Spotify playback."""
    try:
        # Use Spotify API to skip the track
        sp.next_track()
        await ctx.send("skipped that crap, uWu.")
    except Exception as e:
        print(f"Error skipping track: {e}")
        await ctx.send("oh no..are you sure something is playing?")

@bot.command()
async def ping(ctx):
    """Responds with 'heard.' to test bot functionality."""
    await ctx.send("heard.")

def switchitup(action):
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "C:\\Users\\austi\\GitHub\\spot--the-violation-bot\\switchitup.ps1", action])

@bot.event
async def on_disconnect():
    switchitup("stop")
    print("Bot stopped, Spotify output switched back to Default.")

@bot.command()
@allowed_users_only
async def joinmesempai(ctx):
    """Join the user's voice channel."""
    if ctx.author.voice:  # Check if the user is in a voice channel
        channel = ctx.author.voice.channel
        await channel.connect()  # Bot joins the channel
        await ctx.send("hey, I'm in! ready to violate.")
    else:
        await ctx.send("you're not in a voice channel, dummy.")

@bot.command()
@allowed_users_only
async def violatemesempai(ctx):
    """Stream audio from a virtual audio cable."""
    if ctx.voice_client:
        vc = ctx.voice_client
        try:
            print("attempting spotify violations...")
            vc.play(discord.FFmpegPCMAudio(
                source="audio=CABLE Output (VB-Audio Virtual Cable)",
                before_options="-f dshow -analyzeduration 0 -probesize 32",
                options="-ac 2 -ar 48000 -bufsize 256k -threads 2 -vn"
            ))
            vc.play(source, after=lambda e: print(f"Playback finished: {e}"))
            await ctx.send("illegal activities have commenced! enjoy")
        except Exception as e:
            print(f"Error during playback: {e}")
            await ctx.send(f"Error playing audio: {e}")
    else:
        await ctx.send("bring me to the voice channel first, uWu.")

@bot.command()
@allowed_users_only
async def sleepsempai(ctx):
    """Leave the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("legality reestablished.")
    else:
        await ctx.send("I'm not in a voice channel, uWu.")

@bot.command()
async def summon(ctx):
    await ctx.send("I'm here and ready to violate copyright, uWu!")

@bot.command()
async def violateme(ctx):
    responses = [
        "Violation commencing...",
        "you're a dirty girl",
        "get on your knees and throat me",
        "yeah, you like that don't you",
        "stop talking or I'll get the cuffs"
    ]
    response = random.choice(responses)
    await ctx.send(response)

@bot.command()
async def volume(ctx, level: int):
    """Set the playback volume (0-100)."""
    if 0 <= level <= 100:
        # Adjust volume logic here (if possible with FFmpeg)
        await ctx.send(f"Volume set to {level}%.")
    else:
        await ctx.send("Please specify a volume between 0 and 100.")

@bot.command()
async def nightsempai(ctx):
    """Shut down the bot."""
    await ctx.send("Goodbye, uWu!")
    await bot.close()

# Run the bot
bot.run(TOKEN)
