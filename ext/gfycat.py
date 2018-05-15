import aiohttp
import asyncio
import discord
import json

from discord.ext import commands
from random import randint
from settings import GFYCAT_CLIENT_ID, GFYCAT_CLIENT_SECRET

class Gfycat:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def gfycat(self, ctx, *, search: str):
        await ctx.trigger_typing()
        try:
            payload = {'grant_type': 'client_credentials',
                    'client_id': GFYCAT_CLIENT_ID,
                    'client_secret': GFYCAT_CLIENT_SECRET}
            async with aiohttp.ClientSession() as session:
                async with session.post('https://api.gfycat.com/v1/oauth/token', data=json.dumps(payload)) as resp:
                    access_token = await resp.json()
                    access_token = access_token['access_token']

                async with session.get('https://api.gfycat.com/v1/gfycats/search?search_text={}'.format(search),
                                    headers={'Authorization': 'Bearer ' + access_token}) as resp:
                    data = await resp.json()

            await ctx.send('{}'.format(data['gfycats'][randint(0, len(data['gfycats'])-1)]['gifUrl']))
        except Exception as e:
            await ctx.send('No gfycats found for: "{}"'.format(search))

def setup(bot):
    bot.add_cog(Gfycat(bot))