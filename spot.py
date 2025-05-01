import discord
from discord.ext import commands, tasks
import os
import sys
import asyncio
import random
from collections import deque
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

# Load configuration
load_dotenv('botsecs.env')
TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_ID = os.getenv('spoid')
SPOTIFY_SECRET = os.getenv('spoecs')
GPT_KEY = os.getenv('gptkey')
GUILD_ID = int(os.getenv('GUILD_ID', 1140053353615859842))
MUSIC_CHANNEL_ID = int(os.getenv('MUSIC_CHANNEL_ID', 1140053354240815157))
ALLOWED_USERS = {688148738774138913, 472099505269899266, 699750640993173522}

# Discord bot setup
token_missing = [v for v in ('DISCORD_TOKEN','spoid','spoecs','gptkey') if not os.getenv(v)]
if token_missing:
    print(f"Missing env vars: {token_missing}")
    sys.exit(1)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Spotify and OpenAI clients
sp = Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIFY_ID, client_secret=SPOTIFY_SECRET,
                                       redirect_uri='http://localhost:8888/callback',
                                       scope='user-modify-playback-state user-read-playback-state user-read-currently-playing'))
client = OpenAI(api_key=GPT_KEY)

# Shared state
song_queue = deque()
user_contexts = {}

# Decorators
def allowed_users(func):
    async def wrapper(ctx, *args, **kwargs):
        if ctx.author.id in ALLOWED_USERS:
            return await func(ctx, *args, **kwargs)
        await ctx.send("Your taste in music has been deemed not shitty enough to use this command, uWu")
    return commands.check(lambda ctx: ctx.author.id in ALLOWED_USERS)(func)

# Async tasks
@tasks.loop(seconds=5)
async def auto_stream():
    playback = sp.current_playback()
    guild = bot.get_guild(GUILD_ID)
    voice = discord.utils.get(bot.voice_clients, guild=guild)
    if playback and playback.get('is_playing'):
        if not voice:
            channel = guild.get_channel(MUSIC_CHANNEL_ID)
            if isinstance(channel, discord.VoiceChannel):
                try: voice = await channel.connect()
                except: return
        if voice and not voice.is_playing():
            source = discord.FFmpegPCMAudio(source='audio=CABLE Output (VB-Audio Virtual Cable)',
                                            before_options='-f dshow -analyzeduration 0 -probesize 32',
                                            options='-ac 2 -ar 48000 -bufsize 256k -threads 2 -vn')
            voice.play(source)
    elif voice:
        await voice.disconnect()

@tasks.loop(seconds=15)
async def update_status():
    playback = sp.current_playback()
    if playback and playback.get('is_playing'):
        artist = playback['item']['artists'][0]['name']
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=artist))
    else:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name='Spotify Bot'))

@bot.event
async def on_ready():
    auto_stream.start()
    update_status.start()

@bot.event
async def on_message(message):
    if message.author.bot: return
    content = message.content.strip()
    if content.lower().startswith('spot'):
        message.content = '!' + content
    await bot.process_commands(message)

# Utility functions
def get_commands_list():
    return ', '.join(f"!{c.name}" for c in bot.commands)

def fetch_lyrics(song, artist):
    # placeholder: actual API integration
    return None

# Commands
@bot.command()
async def quit(ctx):
    await ctx.send('night, sempai')
    await bot.close()

@bot.command()
async def restart(ctx):
    await ctx.send('Restarting...')
    sys.stdout.flush()
    os.execv(sys.executable, [sys.executable] + sys.argv)

@bot.command()
async def show_emojis(ctx):
    await ctx.send(' '.join(str(e) for e in ctx.guild.emojis))

@bot.command()
async def guild_info(ctx):
    g = ctx.guild
    roles = ', '.join(r.name for r in g.roles if r.name!='@everyone')
    channels = ', '.join(c.name for c in g.channels)
    await ctx.send(f"**{g.name}**: {g.member_count} members, Roles: {roles}, Channels: {channels}")

# Music control
@bot.command()
async def currentsong(ctx):
    p = sp.current_playback()
    if p and p.get('is_playing'):
        item = p['item']
        await ctx.send(f"🎵 {item['name']} by {item['artists'][0]['name']}")
    else:
        await ctx.send('No music playing, uWu')

@bot.command()
@allowed_users
async def play(ctx, *, name):
    res = sp.search(q=name, type='track', limit=1)
    if res['tracks']['items']:
        uri = res['tracks']['items'][0]['uri']
        sp.start_playback(uris=[uri])
        await ctx.send(f"Now playing: {res['tracks']['items'][0]['name']}")
    else:
        await ctx.send('Song not found')

@bot.command()
@allowed_users
async def skip(ctx):
    sp.next_track()
    await ctx.send('Skipped uWu')

@bot.command()
@allowed_users
async def pause(ctx):
    p = sp.current_playback()
    if p and p.get('is_playing'): sp.pause_playback(); await ctx.send('Paused')
    else: sp.start_playback(); await ctx.send('Resumed')

@bot.command()
async def volume(ctx, level: int):
    vc = ctx.voice_client
    if vc and vc.is_playing(): vc.source.volume = max(0, min(1, level/100)); await ctx.send(f"Vol {level}%")
    else: await ctx.send('No audio')

# Queue
@bot.command()
async def add(ctx, *, name):
    r = sp.search(q=name, type='track', limit=1)
    if r['tracks']['items']:
        song_queue.append(r['tracks']['items'][0]['uri'])
        await ctx.send(f"Queued: {r['tracks']['items'][0]['name']}")
    else: await ctx.send('Not found')

@bot.command()
async def show_queue(ctx):
    if song_queue:
        await ctx.send('\n'.join(song_queue))
    else:
        await ctx.send('Queue empty')

# GPT integration
def build_prompt(mood_or_cmd):
    return (
        f"Commands: {get_commands_list()}. "
        f"Input: {mood_or_cmd}" )

# Global dictionary to store conversation context per user:
user_contexts = {}
MAX_CONTEXT_LENGTH = 10  # Maximum conversation turns to keep

def get_guild_summary(ctx):
    g = ctx.guild
    roles   = ', '.join(r.name for r in g.roles     if r.name != '@everyone')
    channels= ', '.join(c.name for c in g.channels)
    return f"{g.name}: {g.member_count} members; Roles: {roles}; Channels: {channels}"

def get_commands_list_text():
    # Mirror get_commands_list(), but returns a plain string
    return ', '.join(f"!{c.name}" for c in bot.commands)

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
        {"role": "system", "content": f"""
    You interpret a Discord bot interaction with Spotify playback functionality.
    Guild information: {guild_context}
    User information: {user_context}

    Supported commands: {get_commands_list_text()}.

    Always respond in EXACTLY ONE of the two following ways:

    - If the input matches a command, reply: "COMMAND: spot<command> [arguments]"
    - If conversational or unclear, reply: "CHAT: <friendly conversational message>"

    Examples:
    User: "Play Shape of You by Ed Sheeran"
    You: COMMAND: spot play Shape of You by Ed Sheeran

    User: "How's your day going?"
    You: CHAT: It's going well, thank you! What music would you like to hear?

    If uncertain, always default to a CHAT response.
    """}
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

    if not (result.startswith("COMMAND:") or result.startswith("CHAT:")):
        result = "CHAT: " + result

 # —— dispatch GPT’s “COMMAND:” or “CHAT:” exactly once ——
    if result.startswith("COMMAND:"):
        # pull out everything after COMMAND:
        command_text = result[len("COMMAND:"):].strip()

        # if it still begins with "spot ", drop that  
        if command_text.lower().startswith("spot "):
            command_text = command_text[5:]

        # make sure it has a "!"
        if not command_text.startswith("!"):
            command_text = f"!{command_text}"

        await ctx.send("Running command")

        # overwrite the same message and dispatch
        ctx.message.content = command_text
        cmd_name = command_text.split()[0].lstrip("!")
        if bot.get_command(cmd_name):
            await bot.process_commands(ctx.message)
        else:
            await ctx.send(f"Error: unknown command '{cmd_name}'")

    elif result.startswith("CHAT:"):
        # normal chat reply
        chat_reply = result[len("CHAT:"):].strip()
        await ctx.send(chat_reply)

    else:
        await ctx.send("Sorry, I couldn’t tell if you wanted a command or just a chat response.")

# Run the bot
bot.run(TOKEN)
