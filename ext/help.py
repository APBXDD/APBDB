import discord

from discord.ext import commands
from settings import *


class Help:
    def __init__(self, bot):
        self.bot = bot
        bot.remove_command('help')  # remove the default help command

    EMBED_COLOR = 0x00FF00

    @commands.group(pass_context=True)
    async def help(self, ctx):
        if ctx.invoked_subcommand is None:
            cmds = [['Admin', 'Admin Commands'],
                    ['General', 'General User Commands'],
                    ['Moderation', 'Mod Commands']]
            e = discord.Embed(title='Help', description=await self.description(cmds), color=self.EMBED_COLOR)
            e.set_footer(text='Example: {}help General'.format(PREFIX))
            await self.bot.say(embed=e)

    @help.command(name='General')
    async def general(self):
        cmds = [['info', 'Show bot information'],
                ['invlink', 'Invite link for the bot'],
                ['serverinfo', 'Show info about the server']]
        e = discord.Embed(title='Help - General', description=await self.description(cmds), color=self.EMBED_COLOR)
        e.set_footer(text='Example: {}info'.format(PREFIX))
        await self.bot.say(embed=e)

    @help.command(name='Admin')
    async def admin(self):
        cmds = [['status avatar [image_link]', 'Change the avatar picture'],
                ['status game [name]', 'Change the current game the bot is playing'],
                ['status prefix [name]', 'Change prefix for commands (requires restart)'],
                ['status username [name]', 'Change bot username'],
                ['leave [server_id]', 'Make the bot leave a server'],
                ['load [extension]', 'Load an extension'],
                ['reload [extension]', 'Reload an extension'],
                ['shutdown', 'Shutdown the bot'],
                ['unload [extension]', 'Unload an extension']]

        e = discord.Embed(title='Help - Admin', description=await self.description(cmds), color=self.EMBED_COLOR)
        e.set_footer(text='Example: {}admin shutdown'.format(PREFIX))
        await self.bot.say(embed=e)

    @help.command(name='Moderation')
    async def moderation(self):
        cmds = [['timeout list', 'Shows currently active timeouts'],
                ['timeout overview', 'Shows users with more than one timeout'],
                ['timeout remove [mention_user]', 'Remove active timeout from mentioned user'],
                ['timeout reset [mention_user]', 'Reset timeouts for mentioned user'],
                ['timeout user [mention_user] [minutes]', 'Timeout mentioned user for x minutes'],
                ['mod add [mention_user]', 'Add a bot mod to the server'],
                ['mod list', 'Shows all bot mods on this server'],
                ['mod remove [mention_user]', 'Remove a bot mod from this server']]

        e = discord.Embed(title='Help - Moderation', description=await self.description(cmds), color=self.EMBED_COLOR)
        e.set_footer(text='Example: {}timeout ...'.format(PREFIX))
        await self.bot.say(embed=e)

    async def description(self, cmds):
        desc = ''
        for cmd in cmds:
            desc += '--------------------------------------------------\n**{0[0]}**: {0[1]}\n'.format(cmd)
        return desc


def setup(bot):
    bot.add_cog(Help(bot))
