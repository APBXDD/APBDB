import aiohttp
import discord
import sqlite3

from discord.ext import commands
from datetime import datetime
from ext.utils import checks
from settings import *


class Admin:
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE)
        self.c = self.connection.cursor()

    @commands.group()
    @checks.is_owner()
    async def admin(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @admin.command(name='announcement')
    async def admin_announcement(self, ctx, *, msg: str):
        """Send an announcement to all server owners"""
        try:
            e = discord.Embed(
                title='Important Announcement',
                description=msg,
                color=0xEEF442
            )

            for guild in self.bot.guilds:
                await guild.owner.send(embed=e)
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            await ctx.send(embed=discord.Embed(
                title='Success', 
                description='Announcement send to {} owners.'.format(len(self.bot.guilds))
            ))


    @admin.group(name='execute')
    async def admin_execute(self, ctx):
        """Execute system operations"""
        if ctx.invoked_subcommand is None:
            pass

    @admin_execute.command(name='sql')
    async def _execute_sql(self, ctx, *, sql: str):
        """Execute SQL Commands"""
        try:
            self.c.execute(sql)
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            await ctx.send(embed=discord.Embed(title="Execution successful", description=sql, color=0x00FF00))
            self.connection.commit()

    @admin.group(name='show')
    async def admin_show(self, ctx):
        """Show system values"""
        if ctx.invoked_subcommand is None:
            pass

    @admin_show.command(name='invites')
    async def _show_invites(self, ctx, *, guildid: int=None):
        """Show invite links by guild ID"""
        await ctx.trigger_typing()
        if guildid is None:
            await ctx.message.channel.send('Guild ID is missing!')
            return

        guild = self.bot.get_guild(guildid)

        if guild is None:
            await ctx.send(embed=discord.Embed(
                title='Error', 
                description='Guild not found.', 
                color=0xFF0000
                ))
            return

        invites = await guild.invites()
        if len(invites) <= 0:
            await ctx.send(embed=discord.Embed(
                title='Error', 
                description='No invites found on this guild.', 
                color=0xFF0000
            ))
            return

        try:
            desc = ''
            for invite in invites:
                desc += '{0.inviter} : {0.channel} : {0.url} \n'.format(invite)
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            await ctx.send(embed=discord.Embed(
                title='Invites from {}'.format(guild.name),
                description=desc
            ))

    @admin_show.command(name='guilds')
    async def _show_guilds(self, ctx):
        """ Shows all servers the bot is currently connected to """
        await ctx.trigger_typing()
        guilds = self.bot.guilds
        if len(guilds) > 0:
            desc = ''
            for guild in guilds:
                desc += '[{0.id}] : {0.name}\n'.format(guild)

            await ctx.send(embed=discord.Embed(
                title='Servers ({})'.format(len(guilds)),
                description=desc,
                color=0x00FF00
            ))
        else:
            await ctx.send(
                title='Error',
                description='Bot is currently not connected to any guilds'
            )

    @admin.command(name='leave')
    async def _admin_leave(self, ctx, guildid: int):
        """Leave a discord server"""
        guild = self.bot.get_guild(id=guildid)
        await guild.leave()
        await ctx.send('Left server {0.name} : {0.id}'.format(guild))

    @admin.command(name='load')
    async def _admin_load(self, ctx, *, ext: str):
        """Loads an extension."""
        try:
            await ctx.send('\N{THINKING FACE} Trying to load ext:  ' + ext)
            self.bot.load_extension('ext.' + ext)
        except Exception as e:
            await ctx.send('\N{CROSS MARK} Failed to load ext: ' + ext)
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{CHECK MARK} Loaded ext: ' + ext)

    @admin.command(name='message')
    async def _admin_message(self, ctx, *, message: str):
        await ctx.send(message)

    @admin.command(name='aprilfools')
    async def _admin_aprilfools(self, ctx, channel: int, *, body: str):
        e = discord.Embed(
            title="Engine Upgrade Release - 20th April 2018",
            description=body,
            url="https://www.youtube.com/watch?v=DLzxrzFCyOs",
            color=0xFF0000,
            timestamp=datetime.now(),
        )

        e.set_author(
            name="Tiggs",
            url="https://uploads.forums.gamersfirst.com/user/450394-tiggs/",
            icon_url="https://uploads.forums.gamersfirst.com/uploads/profile/photo-450394.gif?_r=0",
        )

        channel = ctx.guild.get_channel(channel)

        await channel.send(embed=e)

    @admin.group(name='status')
    async def admin_status(self, ctx):
        """Change status of the bot"""
        if ctx.invoked_subcommand is None:
            pass

    @admin_status.command(name='avatar')
    async def _status_avatar(self, ctx, *, image_link: str):
        """Update bot avatar image"""
        try:
            with aiohttp.ClientSession() as session:
                async with session.get(image_link) as resp:
                    await self.bot.user.edit(avatar=await resp.read())

            self.c.execute('UPDATE bot SET Avatar = ?', [image_link])
        except ValueError as e:
            await ctx.send(embed=discord.Embed(title='Error: Image Error', description=str(e), color=0xFF0000))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=e, color=0xFF0000))
        else:
            self.connection.commit()
            print('[bot]Avatar image updated.')
            await ctx.send(embed=discord.Embed(title='Avatar Image Updated'))

    @admin_status.command(name='game')
    async def _status_game(self, ctx, *, game: str):
        """Update bot game name"""
        try:
            self.c.execute('UPDATE bot SET DefaultGame = ? WHERE ID = 0', [game])
            await self.bot.change_presence(game=discord.Game(name=game))

            self.c.execute('UPDATE bot SET DefaultGame = ?', [game])
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            print('[bot]Status game updated to "{}"'.format(game))
            await ctx.send(embed=discord.Embed(title='Game Update', description='"{}"'.format(game)))

    @admin_status.command(name='prefix')
    async def _status_prefix(self, ctx, *, prefix: str):
        """Update bot prefix
        
            !!! NOT USED/WORKING RIGHT NOW !!!
        """
        try:
            self.c.execute('UPDATE bot SET DefaultPrefix = ?',  [prefix])
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            print('[bot]Status prefix updated to "{}"'.format(prefix))
            await ctx.send(embed=discord.Embed(title='Prefix Update', description='"{}"'.format(prefix)))

    @admin_status.command(name='username')
    async def _status_username(self, ctx, *, username: str):
        """Update bot username"""
        try:
            self.c.execute('UPDATE bot SET UserName = ? WHERE ID = 0', [username])
            await self.bot.user.edit(username=username)

            self.c.execute('UDPATE bot SET UserName = ?', [username])
        except Exception as e:
            await ctx.send(discord.Embed(title='Error', description=str(e)))
        else:
            self.connection.commit()
            print('[bot]Username updated to "{}"'.format(username))
            await ctx.send(embed=discord.Embed(title='Username Update', description='"{}"'.format(username)))

    @admin.command(name='reload')
    async def _admin_reload(self, ctx, *, ext: str):
        """Reloads an extension."""
        try:
            await ctx.send('\N{THINKING FACE} Trying to reload ext: ' + ext)
            self.bot.unload_extension('ext.' + ext)
            self.bot.load_extension('ext.' + ext)
        except Exception as e:
            await ctx.send('\N{CROSS MARK} Failed to reload ext: ' + ext)
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{CHECK MARK} Reloaded ext: ' + ext)

    @admin.command(name='shutdown')
    async def _admin_shutdown(self, ctx):
        """Shuts the bot down
        
            - Closes database connection
            - Logs out of Discord
            - Closes the bot
        """
        await ctx.send(embed=discord.Embed(title='Bot Shutting Down...'))
        print('[exit]Bot is shutting down. Closing services...')
        self.connection.close()
        await self.bot.logout()
        await self.bot.close()

    @admin.command(name='unload')
    async def _admin_unload(self, ctx, *, ext: str):
        """Unloads an extension."""
        try:
            await ctx.send('\N{THINKING FACE} Trying to unload ext:  ' + ext)
            self.bot.unload_extension('ext.' + ext)
        except Exception as e:
            await ctx.send('\N{CROSS MARK} Failed to unload ext: ' + ext)
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{CHECK MARK} Unloaded ext: ' + ext)
            

def setup(bot):
    bot.add_cog(Admin(bot))
