import asyncio
import random
import discord

from settings import *

class BGTasks:
    def __init__(self, bot):
        self.bot = bot
        
        self.bg_game_update_lock = asyncio.Lock()
        self.bg_game_update = bot.loop.create_task(self.bg_game_update())  
    
    async def bg_game_update(self):
        print('[bg] Game Update Task active')
        while not self.bot.is_closed():
            async with self.bg_game_update_lock:
                users, guilds = await self.get_users_and_guilds()

                GAMELIST = [
                    "apbvault.net",
                    'Use {}help'.format(PREFIX),
                    '{}db [query]'.format(PREFIX),
                    '{} users'.format(users),
                    '{} guilds'.format(guilds)
                ]

                game = discord.Game(random.choice(GAMELIST))
                await self.bot.change_presence(status=discord.Status.online, activity=game)
            print('[DEBUG] GAME UPDATE : EVENT : LOOP COMPLETED (900 s)')
            await asyncio.sleep(900)

    async def get_users_and_guilds(self):
        users = sum(1 for i in self.bot.get_all_members())
        guilds = len(self.bot.guilds)
        return users, guilds


def setup(bot):
    bot.add_cog(BGTasks(bot))