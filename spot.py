import discord
from discord.ext import commands
import os
from dotenv import load_dotenv  # For secure token handling
import subprocess


# Load the bot token securely
load_dotenv("botsecs.env")
TOKEN = os.getenv("DISCORD_TOKEN")  # Make sure to set DISCORD_TOKEN in your .env file

# Set up intents and bot
intents = discord.Intents.default()
intents.message_content = True  # Ensure this is enabled in the Developer Portal
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def ping(ctx):
    """Responds with 'heard.' to test bot functionality."""
    await ctx.send("heard.")

def switchitup(action):
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "Path\\To\\audio_switcher.ps1", action])

@bot.event
async def on_ready():
    switchitup("start")
    print("Bot started, Spotify output switched to CABLE Input.")

@bot.event
async def on_disconnect():
    switchitup("stop")
    print("Bot stopped, Spotify output switched back to Default.")


@bot.command()
async def joinmesempai(ctx):
    """Join the user's voice channel."""
    if ctx.author.voice:  # Check if the user is in a voice channel
        channel = ctx.author.voice.channel
        await channel.connect()  # Bot joins the channel
        await ctx.send("hey, I'm in! ready to violate.")
    else:
        await ctx.send("you're not in a voice channel, dummy")

@bot.command()
async def violatemesempai(ctx):
    """Stream audio from a virtual audio cable."""
    if ctx.voice_client:
        vc = ctx.voice_client
        try:
            print("attempting spotify violations...")

            # Define the FFmpeg command manually for debugging
            ffmpeg_command = [
                "ffmpeg",
                "-f", "dshow",
                "-i", "audio=CABLE Output (VB-Audio Virtual Cable)",
                "-f", "wav",
                "pipe:1"
            ]

            # Run the FFmpeg command and capture stderr
            process = subprocess.Popen(
                ffmpeg_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL # Avoid blocking by discarding stderr
            )

            # Attach the FFmpeg output to the bot
            vc.play(discord.PCMAudio(process.stdout))
            await ctx.send("illegal activities have commenced! enjoy")

            # Capture and print FFmpeg logs
            #stderr_output = process.stderr.read().decode("utf-8")
            #print(f"FFmpeg logs:\n{stderr_output}")

        except Exception as e:
            print(f"Error during playback: {e}")
            await ctx.send(f"Error playing audio: {e}")
    else:
        await ctx.send("bring me to the voice channel first, uWu")

@bot.command()
async def sleepsempai(ctx):
    """Leave the voice channel."""
    if ctx.voice_client:  # Check if the bot is in a voice channel
        await ctx.voice_client.disconnect()
        await ctx.send("legality reestablished")
    else:
        await ctx.send("I'm not in a voice channel, uWu")

# Run the bot
bot.run(TOKEN)
