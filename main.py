import asyncio
import re
from urllib import request, parse

import discord
import os
from discord import FFmpegPCMAudio
from discord.ext import commands
import youtube_dl
from youtube_dl import YoutubeDL

Client = discord.Client
client = commands.Bot(command_prefix="-")

ydl_opts = {
    'format': 'bestaudio/best',
    'default search': 'ytsearch',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    "cookiefile": "youtube.com_cookies.txt",
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
ffmpeg_opts = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


@client.event
async def on_ready():
    print("Bot został załadowany!")


queue_song = {}
ytdl = youtube_dl.YoutubeDL(ydl_opts)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_opts), data=data)


async def queue(ctx, url):
    global queue_song
    await ctx.send("Dodano do kolejki")
    urlString = parse.urlencode({'search_query': url})
    html_content = request.urlopen('http://www.youtube.com/results?' + urlString)
    search_content = html_content.read().decode()
    search_results = re.findall(r'\/watch\?v=\w+', search_content)
    result = search_results[0]
    urlFound = str('http://www.youtube.com' + result)
    info_dict = YoutubeDL(ydl_opts).extract_info(urlFound, download=False)
    if info_dict.get('title', None) in queue_song:
        queue_song[str(info_dict['title'])] = url
    else:
        queue_song[str(info_dict['title'])] = url


async def play_song(ctx, url):
    player = await YTDLSource.from_url(url, stream=True)
    async with ctx.typing():
        ctx.voice_client.play(
            player,
            after=lambda e:
            print('Player error: %s' % e) if e else asyncio.run(play_from_queue(ctx)))
    await ctx.send("Teraz gramy: {}".format(player.title))


@client.command(name='play', aliases=['PLAY'])
async def play(ctx, url):
    voiceChannel = ctx.author.voice.channel
    if ctx.voice_client is None:
        voice = await voiceChannel.connect()
    else:
        await ctx.voice_client.move_to(voiceChannel)
        voice = ctx.voice_client
    async with ctx.typing():
        if ctx.voice_client.is_playing():
            await queue(ctx, url)
        else:
            player = await YTDLSource.from_url(url, loop=client.loop, stream=True)
            ctx.voice_client.play(
                player,
                after=lambda e:
                print('Player error: %s' % e) if e else asyncio.run(play_from_queue(ctx)))
    await ctx.send("Teraz gramy: {}".format(player.title))
    while ctx.voice_client.is_playing:
        await asyncio.sleep(60)
    else:
        await ctx.voice_client.disconnect()


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
            message = "**" + str(i + 1) + ".** " + str(keys[i])
            await ctx.send(message)


async def add_to_queue(ctx, url=None):
    await ctx.send("Dodano do kolejki!")
    info_dict = YoutubeDL(ydl_opts).extract_info(url, download=False)
    if info_dict.get('title', None) in queue_song:
        queue_song[str(info_dict['title'])] = url
    else:
        queue_song[str(info_dict['title'])] = url
    pass


async def play_from_queue(ctx):
    global queue_song
    if len(queue_song) != 0:
        keys = list(queue_song.keys())
        values = list(queue_song.values())
        await play_song(ctx, str(values[0]))
        del queue_song[keys[0]]


client.run(os.environ['TOKEN'])