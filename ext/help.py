import discord

from discord.ext import commands
from settings import *


class Help:
    def __init__(self, bot):
        self.bot = bot
        bot.remove_command('help')  # remove the default help command

    EMBED_COLOR = 0x00FF00

    @commands.group(case_insensitive=True)
    async def help(self, ctx):
        if ctx.invoked_subcommand is None:
            cmds = [['Admin', 'Admin Commands'],
                    ['General', 'General User Commands'],
                    ['Moderation', 'Mod Commands'],
                    ['Settings', 'Settings Commands (Server Owner only)'],
                    ['Twitch', 'Twitch Commands'],
                    ['Other', 'Commands for other extensions']]
            e = discord.Embed(title='Help', color=self.EMBED_COLOR)
            e = await self.alt_description(cmds, e)
            e.set_footer(text='Example: {}help General'.format(PREFIX))
            await ctx.send(embed=e)

    @help.command(name='General')
    async def _general(self, ctx):
        cmds = [['avatar (mention)', 'Show the avatar of a user'],
                ['gfycat [search]', 'Search for gifs on Gfycat'],
                ['imgur [search]', 'Search for images / gifs on imgur'],
                ['info', 'Show bot information'],
                ['invlink', 'Invite link for the bot'],
                ['serverinfo', 'Show info about the server'],
                ['sr [search]', 'Search images / gifs on a subreddit']]
        e = discord.Embed(title='Help - General', color=self.EMBED_COLOR)
        e = await self.alt_description(cmds, e)
        e.set_footer(text='Example: {}info'.format(PREFIX))
        await ctx.send(embed=e)

    @help.command(name='Admin')
    async def _admin(self, ctx):
        cmds = [['status avatar [image_link]', 'Change the avatar picture'],
                ['status game [name]', 'Change the current game'],
                ['status prefix [name]', 'Change prefix for commands (requires restart)'],
                ['message [message]', 'Make the bot send a normal message'],
                ['status username [name]', 'Change bot username'],
                ['leave [server_id]', 'Make the bot leave a server'],
                ['load [extension]', 'Load an extension'],
                ['reload [extension]', 'Reload an extension'],
                ['shutdown', 'Shutdown the bot'],
                ['unload [extension]', 'Unload an extension'],
                ['show invites [server_id]', 'Show invite links for a server'],
                ['show guilds', 'Show all servers the bot is currently connected to']]

        e = discord.Embed(title='Help - Admin', color=self.EMBED_COLOR)
        e = await self.alt_description(cmds, e)
        e.set_footer(text='Example: {}admin shutdown'.format(PREFIX))
        await ctx.send(embed=e)

    @help.command(name='Moderation')
    async def _moderation(self, ctx):
        cmds = [['ban [mention] (reason)', 'Ban a user'],
                ['kick [mention] (reason)', 'Kick a user'],
                ['timeout list (page)', 'Shows currently active timeouts'],
                ['timeout overview (page)', 'Shows users with more than one timeout'],
                ['timeout overview user [mention]', 'Shows timeouts for a user'],
                ['timeout remove [mention]', 'Remove active timeout from mentioned user'],
                ['timeout reset [mention]', 'Reset timeouts for mentioned user'],
                ['timeout user [mention] [minutes] (reason)', 'Timeout mentioned user for x minutes']]

        e = discord.Embed(title='Help - Moderation', color=self.EMBED_COLOR)
        e = await self.alt_description(cmds, e)
        e.set_footer(text='Example: {}timeout ...'.format(PREFIX))
        await ctx.send(embed=e)

    @help.command(name='Settings')
    async def _settings(self, ctx):
        cmds = [['activitylog set', 'Set activity log channel'],
                ['activitylog remove', 'Remove activity log channel']]

        e = discord.Embed(title='Help - Settings',color=self.EMBED_COLOR)
        e = await self.alt_description(cmds, e)
        e.set_footer(text='Example: {}settings activitylog ...'.format(PREFIX))
        await ctx.send(embed=e)

    @help.command(name='Twitch')
    async def _twitch(self, ctx):
        cmds = [['twitch add [channel]', 'Add channel to notification list'],
                ['twitch remove [channel]', 'Remove channel from notification list'],
                ['twitch list (page)', 'Show channels in notification list'],
                ['twitch channel [set|remove]', 'Set / remove notification channel']]

        e = discord.Embed(title='Help - Twitch',color=self.EMBED_COLOR)
        e = await self.alt_description(cmds, e)
        e.set_footer(text='Example: {}twitch add ...'.format(PREFIX))
        await ctx.send(embed=e)

    @help.group(name='Other', invoke_without_command=True, case_insensitive=True)
    async def help_other(self, ctx):
        if ctx.invoked_subcommand is None:
            cmds = [['APB', 'APB Game Commands']]
            e = discord.Embed(title='Help - Other', color=self.EMBED_COLOR)
            e = await self.alt_description(cmds, e)
            e.set_footer(text='Example: {}help Other APB'.format(PREFIX))
            await ctx.send(embed=e)

    @help_other.command(name='APB')
    async def _apb(self, ctx):
        cmds = [['apb feed channel [set|remove]', 'Set/Remove Admin Tracker news feed'],
                ['apb feed mod [true|false]', 'Enable/Disable mods in news feed'],
                ['apb feed set [int]', 'Set post ID for news feed'],
                ['db [item_name]', 'Search for a item']]
        e = discord.Embed(title='Help - Other - APB', color=self.EMBED_COLOR)
        e = await self.alt_description(cmds, e)
        e.set_footer(text='Example: {}db ...'.format(PREFIX))
        await ctx.send(embed=e)

    async def alt_description(self, cmds, e):
        for cmd in cmds:
            e.add_field(name=cmd[0], value=cmd[1], inline=False)
        return e

def setup(bot):
    bot.add_cog(Help(bot))
