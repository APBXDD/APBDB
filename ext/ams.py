import asyncio
import discord
import math
import sqlite3

from discord.ext import commands
from ext.utils import checks, embeds
from settings import *
from ext.utils.utils import Message


class AMS:
    """AMS - Automated Moderation System
       
       Made to detect spam, inappropriate content and other types of annoying stuff.

       Features:
       - logging
       - blacklist for text

       WIP:
       - ???

       SoonTM:
       - emoji, mention, reactions spam detection and prevention
    """
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE, isolation_level=None)
        self.c = self.connection.cursor()

        self.debug = False
        self.logging = True
        self.blacklist = True

    EMBED_COLOR = 0xE59900

    async def message_check(self, msg):
        """
            Main message check function
        """
        if self.debug is True : await self.console_message(msg)
        if self.logging is True : await self.log_message(msg)
        if self.blacklist is True : await self.word_filter(msg) 

    async def word_filter(self, msg):
        """
            Checks message for blacklisted words / texts.

            1. Get blacklisted words from db
            2. check if case sensitive or not
            3. Check if string is in the msg.content
            4. Remove message / Keep message
        """
        try:
            guildid = msg.guild.id
        except AttributeError:
            return

        blacklist = self.c.execute('SELECT Blacklisted, CaseSensitive FROM AMSBlacklist WHERE ServerID = ?', [msg.guild.id]).fetchall()

        for blacklisted in blacklist:
            try:
                if blacklisted[1] is 1 and blacklisted[0] in msg.content or blacklisted[1] is 0 and blacklisted[0].lower() in msg.content.lower():
                    await msg.delete()
                    Message(1, '[BLACKLIST][{0.guild}] REMOVED MESSAGE | USER {0.author} ({0.author.id}) '.format(msg))
            except discord.Forbidden:
                Message(3, '[BLACKLIST][{0.guild}] NO PERMISSIONS : {0.channel} ({0.channel.id})'.format(msg))

    async def console_message(self, msg):
        Message(1, '[AMS] {0.created_at} | ID : {0.id} | {0.guild} ({0.guild.id}) | {0.author} ({0.author.id}) | EVERYONE : {0.mention_everyone} | MESSAGE : "{0.content}"'.format(msg))

    async def log_message(self, msg):
        try:
            guildid = msg.guild.id
        except:
            guildid = 0

        if len(msg.embeds) > 0: 
            isembed = True 
        else:
            isembed = False

        try:
            self.c.execute('INSERT INTO AMSlog VALUES (?,?,?,?,?,?,?,?)', (
                msg.id,
                guildid,
                msg.channel.id,
                msg.author.id,
                msg.content,
                msg.mention_everyone,
                msg.created_at,
                isembed
            ))
            self.connection.commit()
        except sqlite3.OperationalError:
            Message(3, '[AMS] DATABASE LOCKED!')

    @commands.group()
    @checks.is_owner_guild()
    @commands.guild_only()
    async def ams(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @ams.command(name="disable")
    async def _ams_disable(self, ctx):
        """
            Disables AMS on a guild
        """
        await self.use_ams(ctx, False)

    @ams.command(name="enable")
    async def _ams_enable(self, ctx):
        """
            Enables AMS in a guild
        """
        await self.use_ams(ctx, True)
    
    async def use_ams(self, ctx, enable: bool):
        self.c.execute('UPDATE servers SET UseAMS = ? WHERE ID = ?', (enable, ctx.message.guild.id))
        self.connection.commit()

        if enable is True:
            description = 'AMS is now active.\nPlease use {}ams level to set the AMS level.'.format(PREFIX)
        else:
            description = 'AMS is now disabled.'

        await ctx.send(embed=discord.Embed(
            title="Automated Moderation System",
            description=description,
            color=self.EMBED_COLOR
        ))

    @ams.command(name="logs")
    async def _ams_logs(self, ctx, *, user: discord.User):
        try:
            if user is not None:
                self.c.execute('SELECT * FROM AMSlog WHERE ServerID = ? AND UserID = ? ORDER BY AMSlog.ID DESC', (
                    ctx.message.guild.id,
                    user.id
                ))
                logs = self.c.fetchall()

                if len(logs) > 0:
                    desc = ''
                    for log in logs[:10]:
                        desc += '**[{0}] {1} :** {2}\n'.format(
                            log[6], 
                            user.name, 
                            '**EMBED**' if log[7] is 1 else log[4]
                        )
                    desc += '\n**{}** messages in this guild.'.format(len(logs))
                else:
                    desc = 'No logs found.'

                e = discord.Embed(
                    title='AMS - Logs - Last messages from {}'.format(user.name),
                    description=desc,
                    color=self.EMBED_COLOR
                )
            else:
                e = discord.Embed(
                    title="Automated Moderation System",
                    description="No ID given.",
                    color=self.EMBED_COLOR
                )
        except Exception as e:
            e = discord.Embed(
                title="AMS - Error",
                description=str(e),
                color=self.EMBED_COLOR
            )

        await ctx.send(embed=e, delete_after=15.0)

    @ams.group(name='filter')
    async def filter(self, ctx):
        # TODO: Add option to enable / disable case-sensitivity 
        #       for already created entries.
        if ctx.invoked_subcommand is None:
            pass

    @filter.command(name='add')
    async def filter_add(self, ctx, *, text: str):
        blacklist = self.c.execute('SELECT Blacklisted FROM AMSBlacklist WHERE ServerID = ?', [ctx.guild.id]).fetchall()

        if not any(text == bltext[0] for bltext in blacklist):
            check_message = await ctx.message.channel.send(embed=discord.Embed(
                title='AMS - Blacklist',
                description='Enable case-sensitivity for blacklisted text: **{0}**?\n'\
                            'Yes / No to enable / disable.'.format(text),
                color=0x000000
            ))

            def check(m):
                if m.channel == ctx.message.channel and ctx.message.author is m.author:
                    return m.content.lower() == 'yes' or m.content.lower() == 'no'

            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                e = discord.Embed(
                    title='AMS - Blacklist - Canceled',
                    description='No response received.',
                    color=0x000000
                )
                await check_message.edit(embed=e)
                return
            else:
                await msg.delete()
                if msg.content.replace('{0}ams filter add '.format(PREFIX), '').lower() == 'yes':
                    enable = True
                else:
                    enable = False

            self.c.execute('INSERT INTO AMSBlacklist (ServerID, Blacklisted, CaseSensitive) VALUES (?, ?, ?)', 
                          (ctx.guild.id, text, enable))

            description = '**{0}** is now blacklisted on this server.'.format(text)
        else:
            description = '**{0}** is already blacklisted on this server.'.format(text)

        e = discord.Embed(
            title='AMS - Blacklist',
            description=description,
            color=0x000000,
        )
        e.set_footer(text='You can remove blacklisted text with {0}ams filter remove [text]'.format(PREFIX))
        self.connection.commit()
        await ctx.send(embed=e)
    
    @filter.command(name='remove')
    async def filter_remove(self, ctx, *, text: str):
        blacklist = self.c.execute('SELECT Blacklisted FROM AMSBlacklist WHERE ServerID = ?', [ctx.guild.id]).fetchall()
        
        if any(text == bltext[0] for bltext in blacklist):
            self.c.execute('DELETE FROM AMSBlacklist WHERE ServerID = ? AND Blacklisted = ?', 
                            (ctx.guild.id, text))

            description='**{0}** removed from the blacklist.'.format(text)
        else:
            description = '**{0}** is not blacklisted on this server.'.format(text)

        e = discord.Embed(
            title='AMS - Blacklist',
            description=description,
            color=0x000000,
        )
        e.set_footer(text='You can clear the blacklist with {0}ams filter clear'.format(PREFIX))
        self.connection.commit()
        await ctx.send(embed=e)
    
    @filter.command(name='clear')
    async def filter_clear(self, ctx):
        e = discord.Embed(
            title='AMS - Blacklist - Clear',
            description='Are you sure you want to remove all text filters?\nThis **cannot** be undone!',
            color=0x000000
        )
        e.set_footer(text='Type "yes" to confirm deletion')
        clear_msg = await ctx.send(embed=e)

        def check(m):
            return m.content == 'yes' and m.channel == ctx.message.channel and ctx.message.author is m.author

        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            await msg.delete()
        except asyncio.TimeoutError:
            e = discord.Embed(
                title='AMS - Blacklist - Clear canceled',
                description='Blacklist was not cleared!',
                color=0x000000
            )
            await clear_msg.edit(embed=e)
            return

        try:
            self.c.execute('DELETE FROM AMSBlacklist WHERE ServerID = ?', [ctx.guild.id])

            e = discord.Embed(
                title='AMS - Blacklist - Cleared!',
                description='Blacklist was cleared!',
                color=0x000000
            )
        except Exception as e:
            await ctx.send(embed=await embeds.default_exception(e))
        else:
            self.connection.commit()
            await clear_msg.edit(embed=e)

    @filter.command(name='list')
    async def filter_list(self, ctx, *, page: int = None):
        blacklist = self.c.execute('SELECT Blacklisted, CaseSensitive FROM AMSBlacklist WHERE ServerID = ?', [ctx.guild.id]).fetchall()
        per_embed = 15
        page = 1 if page is None or page < 1 or page > math.ceil(len(blacklist) / per_embed) else page 

        desc = 'Blacklisted text on this server:\n\n'\
               'Case Sensitive | Blacklisted String\n' 
        for blacklisted in blacklist[(0 + (per_embed * (page - 1))):(per_embed + (per_embed * (page - 1)))]:
            desc += '{0[1]} | **{0[0]}**\n'.format(blacklisted)

        e = discord.Embed(
            title='AMS - Blacklist',
            description=desc,
            color=0x000000,
        )

        e.set_footer(text='Page {} of {} | {} blacklisted'.format(
                page,
                math.ceil(len(blacklist) / per_embed),
                len(blacklist)
            )
        )

        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(AMS(bot))
