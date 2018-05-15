import asyncio
import discord
import sqlite3

from datetime import datetime
from discord.ext import commands
from settings import *

ext = True

try:
    from pypubg import core
except ImportError:
    ext = False

class PUBG:
    def __init__(self, bot):
        self.bot = bot
        self.api = core.PUBGAPI(self.API_KEY)

    API_KEY = PUBG_API_KEY
    EMBED_COLOR = 0xf4bc42

    @commands.command()
    async def pubg(self, ctx, user: str=None, mode: str='solo', region: str='agg'):
        await ctx.trigger_typing()
        if user is None:
            e = discord.Embed(
                title='PUBG Plugin Usage',
                description='How to use PUBG commands',
                color=self.EMBED_COLOR
            )

            e.add_field(
                name='Player Stats', 
                value='{}pubg [playername] (solo/duo/squad) (as/na/agg/sea/eu/oc/sa)'.format(PREFIX)
            )
            await ctx.send(embed=e)
        else:
            try:
                player = self.api.player(user)
                stats = await self.get_mode_stats(ctx, player, mode, region)

                e = discord.Embed(
                    title='Player Stats',
                    description='**Season:** {}\n'
                                '**Region:** {}\n'
                                '**Match:** {}'.format(stats['Season'], stats['Region'], stats['Match']),
                    color=self.EMBED_COLOR,
                    timestamp=datetime.strptime(player['LastUpdated'][:19], "%Y-%m-%dT%H:%M:%S")
                )

                for stat in stats['Stats'][:5]:
                    e.add_field(name=stat['label'], value=stat['displayValue'])

                e.set_author(
                    name=player['PlayerName'], 
                    icon_url=player['Avatar'], 
                    url='https://pubgtracker.com/profile/pc/{}'.format(user)
                )
                e.set_footer(text='Last Update')
            except KeyError as e:
                await ctx.send(embed=discord.Embed(
                    title='Error', 
                    description='Player Not Found', 
                    color=self.EMBED_COLOR
                ))
            else:
                await ctx.send(embed=e)

    async def get_mode_stats(self, ctx, data, mode, region):
        try:
            stats = []
            for stat in data['Stats']:
                if stat['Match'] == mode and stat['Region'] == region:
                    stats.append(stat)
            return stats[0]
        except IndexError:
            await ctx.send(embed=discord.Embed(
                title='Error',
                description='Season and Region combination not found.'
            ))


def setup(bot):
    if ext is True:
        bot.add_cog(PUBG(bot))
    else:
        print('[exts]Extension "pubg" not loaded. Missing pypubg! (pip install pypubg)')
        raise ImportError
