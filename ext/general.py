import aiohttp
import discord

from discord.ext import commands
from settings import *


class General:
    def __init__(self, bot):
        self.bot = bot

    __version__ = '0.1.0'

    @commands.command()
    async def info(self):
        await self.bot.say(embed=discord.Embed(
            title='Info',
            description='**Creator:** Speed#8053\n'
                        '**Version:** {0}\n'
                        '**Library:** Discord.py {1}'
                        .format(self.__version__, discord.__version__),
            color=0x00FF00))

    @commands.command()
    async def invlink(self):
        e = discord.Embed(title='Invite Link',
                          description=INVITE_LINK.format(self.bot.user.id, '0'),
                          url=INVITE_LINK.format(self.bot.user.id, '0'))
        e.set_footer(text='Use this link to invite the bot to your server!')
        e.set_thumbnail(url='https://discordapp.com/assets/fc0b01fe10a0b8c602fb0106d8189d9b.png')
        await self.bot.say(embed=e)

    @commands.command(pass_context=True)
    async def serverinfo(self, ctx):
        """Displays information about the current server"""
        e = discord.Embed(title=ctx.message.server.name, color=0x00FF00)
        e.add_field(name='Server ID', value=ctx.message.server.id)
        e.add_field(name='Owner', value=ctx.message.server.owner)
        e.add_field(name='Region', value=ctx.message.server.region)
        e.add_field(name='Created At', value=ctx.message.server.created_at)
        e.add_field(name='Members', value=str(ctx.message.server.member_count))
        e.add_field(name='Channels', value=str(len(ctx.message.server.channels)))
        e.set_thumbnail(url=ctx.message.server.icon_url)
        await self.bot.say(embed=e)

    @commands.command(pass_context=True)
    async def gif(self, search: str):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.gfycat.com/v1test/gfycats/search?search_text={}'.format(search)) as resp:
                gifs = await resp.json()


def setup(bot):
    bot.add_cog(General(bot))
