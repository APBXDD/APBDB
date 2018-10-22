import asyncio
import discord
import sqlite3

from discord.ext import commands
from random import choice
from settings import *
from ext.utils.utils import Message

ext = True
try:
    from imgurpython import ImgurClient
except ImportError:
    ext = False

class Imgur:
    def __init__(self, bot):
        self.bot = bot

        self.imgur_client = ImgurClient(IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET)

    @commands.command()
    async def imgur(self, ctx, *, search: str = None):
        await ctx.trigger_typing()
        try:
            if search is not None:
                images = self.imgur_client.gallery_search(search)
                image = choice(images)
                if await self.nsfw_check(image, ctx.message.channel) is True:
                    await ctx.send(image.link)
            else:
                await ctx.send('No search query set.')
        except IndexError as e:
            await ctx.send('Nothing found for: {}'.format(search))

    @commands.command()
    async def memes(self, ctx):
        try:
            await ctx.trigger_typing()
            images = self.imgur_client.default_memes()
            image = choice(images)
            if await self.nsfw_check(image, ctx.message.channel) is True:
                await ctx.send(image.link)
        except IndexError as e:
            await ctx.send('Error: Nothing found.')

    @commands.command(pass_context=True)
    async def sr(self, ctx, *, search: str):
        await ctx.trigger_typing()
        try:
            if search is not None:
                images = self.imgur_client.subreddit_gallery(search)
                image = choice(images)
                if await self.nsfw_check(image, ctx.message.channel) is True:
                    await ctx.send(image.link)
            else:
                await ctx.send('No search query set.')
        except IndexError as e:
            await ctx.send('Nothing found for: {}'.format(search))

    async def nsfw_check(self, image, channel):
        if image.nsfw is False:
            return True
        elif image.nsfw is True and channel.is_nsfw():
            return True
        await channel.send('**NSFW Picture**: Please only lookup nsfw content in **nsfw** channels.')
        return False

def setup(bot):
    if ext is True:
        bot.add_cog(Imgur(bot))
    else:
        Message(2, '[EXTENSION] "imgur" not loaded. Missing imgurpython! (pip install imgurpython)')
        raise ImportError
