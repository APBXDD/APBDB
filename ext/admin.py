import aiohttp
import discord
import sqlite3

from discord.ext import commands
from ext.utils import checks
from settings import *


class Admin:
    def __init__(self, bot):
        self.bot = bot
        self.connection = sqlite3.connect(DATABASE)

    @commands.group(pass_context=True, hidden=True)
    @checks.is_owner()
    async def admin(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @admin.command(name='leave', hidden=True)
    async def admin_leave(self, server_id: str):
        """Leave a discord server"""
        await self.bot.leave_server(self.bot.get_server(id=server_id))

    @admin.command(name='load', hidden=True)
    async def admin_load(self, *, ext: str):
        """Loads an extension."""
        try:
            await self.bot.say('\N{THINKING FACE} Trying to load ext:  ' + ext)
            self.bot.load_extension('ext.' + ext)
        except Exception as e:
            await self.bot.say('\N{CROSS MARK} Failed to load ext: ' + ext)
            await self.bot.say('{}: {}'.format(type(e).__name__, e))
        else:
            await self.bot.say('\N{CHECK MARK} Loaded ext: ' + ext)

    @admin.group(pass_context=True, name='status')
    async def admin_status(self, ctx):
        """Change status of the bot"""
        if ctx.invoked_subcommand is None:
            pass

    @admin_status.command(name='avatar')
    async def status_avatar(self, image_link: str):
        """Update bot avatar image"""
        try:
            with aiohttp.ClientSession() as session:
                async with session.get(image_link) as resp:
                    await self.bot.edit_profile(avatar=await resp.read())
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=e, color=0xFF0000))
        else:
            self.connection.commit()
            print('[bot]Status avatar image updated.')
            await self.bot.say(embed=discord.Embed(title='Avatar Image Updated'))

    @admin_status.command(name='game')
    async def status_game(self, game: str):
        """Update bot game name"""
        try:
            c = self.connection.cursor()
            c.execute('UPDATE bot SET DefaultGame = "{}" WHERE ID = 0'.format(game))
            await self.bot.change_presence(game=discord.Game(name=game))
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            print('[bot]Status game updated to "{}"'.format(game))
            await self.bot.say(embed=discord.Embed(title='Game Update', description='"{}".'.format(game)))

    @admin_status.command(name='prefix')
    async def status_prefix(self, prefix: str):
        """Update bot game name"""
        try:
            c = self.connection.cursor()
            c.execute('UPDATE bot SET DefaultPrefix = "{}" WHERE ID = 0'.format(prefix))
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            print('[bot]Status prefix updated to "{}"'.format(prefix))
            await self.bot.say(embed=discord.Embed(title='Prefix Update', description='"{}".'.format(prefix)))

    @admin_status.command(name='username')
    async def status_username(self, username: str):
        """Update bot username"""
        try:
            c = self.connection.cursor()
            c.execute('UPDATE bot SET UserName = "{}" WHERE ID = 0'.format(username))
            await self.bot.edit_profile(username=username)
        except Exception as e:
            await self.bot.say(discord.Embed(title='Error', description=str(e)))
        else:
            self.connection.commit()
            print('[bot]Username updated to "{}"'.format(username))
            await self.bot.say(embed=discord.Embed(title='Username Update', description='"{}".'.format(username)))

    @admin.command(name='reload', hidden=True)
    async def admin_reload(self, *, ext: str):
        """Reloads an extension."""
        try:
            await self.bot.say('\N{THINKING FACE} Trying to reload ext: ' + ext)
            self.bot.unload_extension('ext.' + ext)
            self.bot.load_extension('ext.' + ext)
        except Exception as e:
            await self.bot.say('\N{CROSS MARK} Failed to reload ext: ' + ext)
            await self.bot.say('{}: {}'.format(type(e).__name__, e))
        else:
            await self.bot.say('\N{CHECK MARK} Reloaded ext: ' + ext)

    @admin.command(name='shutdown')
    async def admin_shutdown(self):
        """Shuts the bot down
        
            - Closes database connection
            - Logs out of Discord
            - Closes the bot
        """
        await self.bot.say(embed=discord.Embed(title='Admin: Bot Shutting Down...'))
        self.connection.close()
        self.bot.logout()
        self.bot.close()

    @admin.command(name='unload', hidden=True)
    async def admin_unload(self, *, ext: str):
        """Unloads an extension."""
        try:
            await self.bot.say('\N{THINKING FACE} Trying to unload ext:  ' + ext)
            self.bot.unload_extension('ext.' + ext)
        except Exception as e:
            await self.bot.say('\N{CROSS MARK} Failed to unload ext: ' + ext)
            await self.bot.say('{}: {}'.format(type(e).__name__, e))
        else:
            await self.bot.say('\N{CHECK MARK} Unloaded ext: ' + ext)


def setup(bot):
    bot.add_cog(Admin(bot))
