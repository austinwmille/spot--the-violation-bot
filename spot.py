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
from openai import OpenAI

# Load tokens securely
load_dotenv("botsecs.env")
TOKEN = os.getenv("DISCORD_TOKEN")  # Make sure to set DISCORD_TOKEN in your .env file
spoid = os.getenv("spoid")
spoecs = os.getenv("spoecs")
gptkey = os.getenv("gptkey")

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
ALLOWED_USER_IDS = [688148738774138913,
                    472099505269899266,
                    #764260458898915345
                    ]  # Add your ID and the other user's ID

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

@bot.command()
async def show_emojis(ctx):
    emojis = [str(emoji) for emoji in ctx.guild.emojis]
    await ctx.send(f"Available emojis: {' '.join(emojis)}")

@bot.command()
async def greet(ctx):
    custom_emoji = "<:smile:123456789012345678>"
    await ctx.send(f"Hello! {custom_emoji}")

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
    help_message = """```diff
+ Spot, the Violation Bot - Commands:
    
🎶 Spotify Controls:
- !joinmesempai     -> Join voice chat.
- !violatemesempai  -> Stream Spotify through bot.
- !hitmesempai      -> Pause/resume Spotify.
- !skipthissempai   -> Skip the current track.
- !sleepsempai      -> Leave voice chat.
- !play <song>      -> Search & play a song.
- !currentsong      -> Show currently playing song.
- !volume <0-100>   -> Set bot volume (WIP).

🛠️ Bot & Misc:
- !show_emojis      -> Show available emojis.
- !violateme        -> Get a random, dirty response.
- !summon           -> Make the bot say something dumb.
- !ping             -> Check if the bot is working.
- !nightsempai      -> Shut down the bot.

GPT AI Commands:
- !hey <question>   -> Ask the bot an existential crisis.

*Bask in my ~~love~~--glory, uWu*
"""
    await ctx.send(help_message)

@bot.command()
@allowed_users_only
async def currentsong(ctx):
    """Display the currently playing Spotify song."""
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
    """Search for and play a song on Spotify."""
    results = sp.search(q=song_name, type="track", limit=1)
    if results['tracks']['items']:
        track_uri = results['tracks']['items'][0]['uri']
        sp.start_playback(uris=[track_uri])
        await ctx.send(f"Now playing: {results['tracks']['items'][0]['name']}")
    else:
        await ctx.send("Song not found.")

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
    response = random.choice(responses)
    await ctx.send(response)

@bot.command()
@allowed_users_only
async def volume(ctx, level: int):
    """Set the playback volume (0-100)."""
    if 0 <= level <= 100:
        # Adjust volume logic here (if possible with FFmpeg)
        # trying the following line of logic to see if it works
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.source.volume = level / 100
            await ctx.send(f"Volume set to {level}%.")
        else:
            await ctx.send("No audio is currently playing.")
    else:
        await ctx.send("Please specify a volume between 0 and 100.")

@bot.command()
async def shutdown(ctx):
    """Manually shut down the bot and reset Spotify output."""
    await ctx.send("Goodbye, uWu!")
    switchitup("stop")  # Reset Spotify before shutting down
    await bot.close()

@bot.command()
async def nightsempai(ctx):
    """Shut down the bot."""
    await ctx.send("Goodbye, uWu!")
    await bot.close()

# ----------------this last command is the GPT api inclusion --------------------

client = OpenAI(
    api_key=gptkey
)

user_context = {}

@bot.command()
@commands.cooldown(1, 4, commands.BucketType.user)  # 1 use every 4 seconds
async def hey(ctx, *, question: str):
    '''
    The following adds in a 'memory' for each user
    '''
    user_id = ctx.author.id
    if user_id not in user_context:
        user_context[user_id] = [{"role": "system", "content": "You are Discord bot assistant with subtle anti-capitalist, and existential undertones. You try to be nice and helpful but don't really care."}]
    
    user_context[user_id].append({"role": "user", "content": question})
    """
    Ask GPT a question and get a response.
    Example: !askgpt What is the capital of France?
    """
    try:
        # Show typing indicator
        await ctx.channel.typing()

        # Call the OpenAI API
        response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=user_context[user_id],
            max_tokens=771,
            temperature=0.6
        )

        # Extract the response content
        answer = response.choices[0].message.content
        user_context[user_id].append({"role": "assistant", "content": answer})

        # Send the GPT response to Discord
        await ctx.send(answer)

    except Exception as e:
        print(f"Error with GPT request: {e}")
        await ctx.send("Sorry, something went wrong with GPT. Please try again.")

# Run the bot
bot.run(TOKEN)
