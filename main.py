import asyncio
import discord
import os
from discord.ext import commands
import youtube_dl
from youtube_dl import YoutubeDL

Client = discord.Client
client = commands.Bot(command_prefix="-")

ydl_opts = {
    'format': 'bestaudio/best',
    'default search': 'ytsearch',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192'
    }]
}
ffmpeg_opts = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}
queue_song = {}


@client.event
async def on_ready():
    print("Bot został załadowany!")


async def play_url(ctx, url):
    try:
        os.remove("muzyka.mp3")
    except:
        pass

    url = str(url)
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    for file in os.listdir("./"):
        if file.endswith(".mp3"):
            os.rename(file, "muzyka.mp3")
    voice.play(discord.FFmpegPCMAudio("muzyka.mp3"), after=lambda e: asyncio.run(queue(ctx)))
    voice.source = discord.PCMVolumeTransformer(voice.source)


@client.command(name='play', aliases=['PLAY'])
async def play(ctx, url):
    global voice
    user = ctx.message.author
    voiceChannel = user.voice.channel
    channel = ctx.author.voice.channel
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice == None:
        await voiceChannel.connect()
    else:
        await voice.move_to(channel)
    song_there = os.path.isfile("muzyka.mp3")
    try:
        if song_there:
            os.remove("muzyka.mp3")
    except PermissionError:
        return

    if voice.is_playing():
        await ctx.send("Muzyka już gra, jeśli chcesz ją zakolejkować to wpisz '-queue'")
    else:
        await play_url(ctx, url)
    await asyncio.sleep(60)
    while voice.is_playing():
        break
    else:
        await voice.disconnect()


async def queue(ctx):
    global queue_song
    if len(queue_song) != 0:
        keys = list(queue_song.keys())
        values = list(queue_song.values())
        await play_url(ctx, str(values[0]))
        del queue_song[keys[0]]


@client.command(name='pause', aliases=['PAUSE'])
async def pause(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
    else:
        await ctx.send("Nic na razie nie gra.")

async def loading(ctx):
    await ctx.send("Wczytywanie muzyki...")


@client.command(name='resume', aliases=['RESUME'])
async def resume(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        voice.resume()
    else:
        await ctx.send("Muzyka nadal gra albo nic nie gra.")


@client.command(name='stop', aliases=['STOP'])
async def stop(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing() or len(queue_song) >= 1:
        queue_song.clear()
        voice.stop()
    else:
        await ctx.send("Nic nie gra lub kolejka jest pusta")


@client.command(name='skip', aliases=['SKIP'])
async def skip(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing() or len(queue_song) >= 1:
        voice.stop()
    else:
        await ctx.send("Nic nie gra lub kolejka jest pusta")


@client.command(name='pomoc', aliases=['POMOC'])
async def command_list(ctx):
    commands = "-stop = zatrzymuje muzykę \n" \
               "-skip = pomija muzykę i idzie do następnej\n" \
               "-pause = zatrzymuje muzykę z możliwością kontynuacji \n" \
               "-resume = kontynuuje spauzowaną muzykę\n" \
               "-check = sprawdza zawartość kolejki\n" \
               "-play + url = pobiera muzykę z url a następnie odtwarza ją"
    await ctx.send(commands)


@client.command(name='check', aliases=['CHECK'])
async def check(ctx):
    values = list(queue_song.values())
    keys = list(queue_song.keys())
    if len(queue_song) < 1:
        await ctx.send("Kolejka jest pusta")
    else:
        await ctx.send("Następne w kolejce:")
        for i in range(len(keys)):
            info_dict = YoutubeDL(ydl_opts).extract_info(values[i], download=False)
            print(info_dict)
            message = "**" + str(i + 1) + ".** " + str(keys[i]) + ")"
            await ctx.send(message)


@client.command(name='queue', aliases=['QUEUE'])
async def add_to_queue(ctx, url):
    await ctx.send("Dodano do kolejki!")
    info_dict = YoutubeDL(ydl_opts).extract_info(url, download=False)
    if info_dict.get('title', None) in queue_song:
        queue_song[str(info_dict['title'])] = url
    else:
        queue_song[str(info_dict['title'])] = url
    pass


client.run(os.environ['TOKEN'])
