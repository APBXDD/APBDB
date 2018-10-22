import aiohttp
import discord
import json

from discord.ext import commands
from random import choice
from settings import *


class General:
    def __init__(self, bot):
        self.bot = bot
        
    __version__ = '0.9.8'

    __updated__ = '03.10.2018'

    @commands.command(pass_context=True)
    async def avatar(self, ctx, *, member: discord.Member = None):
        try:
            if member is not None:
        	    avatar_url = member.avatar_url
            else:
                avatar_url = ctx.message.author.avatar_url
        except Exception as e:
            await ctx.send("Error: {}".format(e))
        else:
            await ctx.send(avatar_url)

    @commands.command()
    async def info(self, ctx):
        e = discord.Embed(
            title='{}'.format(self.bot.user.name),
            description='**Creator:** Speed#0001 (135822605583253504)\n'
                        '**Version:** {0} ({1})\n'
                        '**Library:** Discord.py {2}\n'
                        '**Guilds:** {3}\n'
                        '**Channels:** {4}\n'
                        '**Users:** {5}'
                        .format(
                            self.__version__, 
                            self.__updated__, 
                            discord.__version__, 
                            len(self.bot.guilds),
                            sum(1 for i in self.bot.get_all_channels()),
                            sum(1 for i in self.bot.get_all_members()),
                        ),
            color=0x00FF00)
        e.set_thumbnail(url=self.bot.user.avatar_url)
        await ctx.send(embed=e)

    @commands.command()
    async def invlink(self, ctx):
        e = discord.Embed(title='Invite Link',
                          description=INVITE_LINK.format(self.bot.user.id, '0'),
                          url=INVITE_LINK.format(self.bot.user.id, '0'))
        e.set_footer(text='Use this link to invite the bot to your server!')
        e.set_thumbnail(url='https://discordapp.com/assets/fc0b01fe10a0b8c602fb0106d8189d9b.png')
        await ctx.send(embed=e)

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx, *, guildid: int = None):
        """Displays information about the current server"""

        if guildid is not None:
            guild = self.bot.get_guild(id=guildid)
        else:
            guild = ctx.message.guild

        try:
            e = discord.Embed(title=guild.name, color=0x00FF00)
            e.add_field(name='ID', value=guild.id, inline=False)
            e.add_field(name='Owner', value=guild.owner, inline=False)
            e.add_field(name='Region', value=guild.region, inline=False)
            e.add_field(name='Created At', value=guild.created_at, inline=False)
            e.add_field(name='Members', value=str(guild.member_count), inline=False)
            e.add_field(name='Channels', value=str(len(guild.channels)), inline=False)
            e.set_thumbnail(url=guild.icon_url)
        except AttributeError as e:
            e = discord.Embed(
                title="Error - Guild Not Found",
                description=str(e),
                color=0xFF0000
            )
        await ctx.send(embed=e)

def setup(bot):
    bot.add_cog(General(bot))
