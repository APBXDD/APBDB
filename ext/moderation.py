import asyncio
import discord
import sqlite3


from datetime import datetime, timedelta
from discord.ext import commands
from ext.utils import checks, embeds
from settings import *


class Moderation:
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE)
        self.c = self.connection.cursor()

        self.timeout_lock = asyncio.Lock()
        self.timeout_check = bot.loop.create_task(self.timeout_check())

    def __del__(self):
        self.timeout_check.cancel()

    @commands.command()
    @checks.can_manage()
    async def ban(self, ctx, member: discord.Member=None, *, reason: str=None):
        """Ban a user from the discord guild"""

        if member is None:
            await ctx.send(embed=discord.Embed(
                title='Error', 
                description='Please mention a user to ban.\n{}ban [mention] (reason)'.format(PREFIX)
            ))
        else:
            ban_message = await ctx.message.channel.send(embed=discord.Embed(
                title='Ban - {0.display_name}'.format(member),
                description='Do you really want to ban {0.display_name}?\n\n'
                            '**Original Name**: {0}\n'
                            '**ID**: {0.id}\n\n'
                            'Type "confirm" to ban user'.format(member),
                color=0xFF0000
            ))

            def check(m):
                return m.content == 'confirm' and m.channel == ctx.message.channel and ctx.message.author is m.author

            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                await msg.delete()
            except asyncio.TimeoutError:
                e = discord.Embed(
                    title='Ban canceled',
                    description='{0.name} was not banned.'.format(member),
                    color=0x00FF00
                )
                await ban_message.edit(embed=e)
                return

            try:
                await member.ban(reason=reason, delete_message_days=0)
                e = embed=discord.Embed(
                    title='Banned - {0} ({0.id})'.format(member),
                    description='{0.name} banned from this server.'.format(member),
                    color=0xFF0000
                )
                e.set_author(name=ctx.message.author, url=ctx.message.author.avatar_url)
                e.set_footer(text=member, icon_url=member.avatar_url)
                await ban_message.edit(embed=e)
            except Exception as e:
                await ctx.send(embed=await embeds.default_exception(e))
            finally:
                channelid = await self.get_activitylog_channel(ctx.message.guild.id)
                if channelid is not None:
                    channel = ctx.message.guild.get_channel(channelid)
                    e = discord.Embed(
                        title='Ban', 
                        description='**Reason**: {}'.format(reason),
                        color=0xf4f142,
                        timestamp=datetime.now()
                    )
                    e.add_field(name='User', value=str(member), inline=False)
                    e.add_field(name='ID', value=str(member.id), inline=False)
                    e.set_footer(text=ctx.message.author, icon_url=ctx.message.author.avatar_url)
                    await channel.send(embed=e)

    @commands.command()
    @checks.can_manage()
    async def kick(self, ctx, member: discord.Member=None, *, reason: str=None):
        """ Kick a user from the guild """

        if member is None:
            await ctx.send(embed=discord.Embed(
                title='Error', 
                description='Please mention a user to kick.\n{}kick [mention] (reason)'.format(PREFIX)
            ))
        else:
            kick_message = await ctx.message.channel.send(embed=discord.Embed(
                title='Kick - {0.display_name}'.format(member),
                description='Do you really want to kick {0.display_name}?\n\n'
                            '**Original Name**: {0}\n'
                            '**ID**: {0.id}\n\n'
                            'Type "confirm" to kick user'.format(member),
                color=0xFF0000
            ))

            def check(m):
                return m.content == 'confirm' and m.channel == ctx.message.channel and ctx.message.author is m.author

            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                await msg.delete()
            except asyncio.TimeoutError:
                e = discord.Embed(
                    title='Kick canceled',
                    description='{0.name} was not kicked.'.format(member),
                    color=0x00FF00
                )
                await kick_message.edit(embed=e)
                return
                
            try:
                await member.kick(reason=reason)
                e = discord.Embed(
                    title='Kicked - {0} ({0.id})'.format(member),
                    description='{0.name} kicked from this server.'.format(member),
                    color=0xFF0000
                )
                e.set_author(name=ctx.message.author, url=ctx.message.author.avatar_url)
                e.set_footer(text=member, icon_url=member.avatar_url)
                await kick_message.edit(embed=e)
            except Exception as e:
                await ctx.send(embed=await embeds.default_exception(e))
            finally:
                channelid = await self.get_activitylog_channel(ctx.message.guild.id)
                if channelid is not None:
                    channel = ctx.message.guild.get_channel(channelid)
                    e = discord.Embed(
                        title='Kick', 
                        description='**Reason**: {}'.format(reason),
                        color=0xf4f142,
                        timestamp=datetime.now()
                    )
                    e.add_field(name='User', value=str(member), inline=False)
                    e.add_field(name='ID', value=str(member.id), inline=False)
                    e.set_footer(text=ctx.message.author, icon_url=ctx.message.author.avatar_url)
                    await channel.send(embed=e)

    @commands.command()
    @checks.can_manage()
    async def prune(self, ctx, amount: int, member: discord.Member=None):
        """Prune x amount of messages"""
        try:
            if member is None:
                await ctx.channel.purge(limit=amount)
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e)))

    @commands.group()
    @checks.can_manage()
    async def timeout(self, ctx):
        """ Timeout commands
            - requires manage message permissions
        """
        if ctx.invoked_subcommand is None:
            pass

    @timeout.command(name='list')
    async def timeout_list(self, ctx, *, page: int=1):
        """Lists all current timeouts for the guild"""
        try:
            self.c.execute('SELECT MemberID, TimeoutTime, TimeInMinutes, TimeoutCount '
                           'FROM timeouts '
                           'WHERE ServerID = ? '
                           'AND Enabled = 1 '
                           'LIMIT 10 OFFSET ?', (ctx.message.guild.id, ((page - 1) * 10)))
            timeouts = self.c.fetchall()

            e = discord.Embed(title='Timeout List (Active Timeouts)')
            e.set_footer(text='Page {}'.format(page))
            if len(timeouts) > 0: 
                for timeout in timeouts:
                    member = ctx.message.guild.get_member(int(timeout[0]))
                    user = self.bot.get_user(int(timeout[0]))
                    time_until_timeout = datetime.strptime(str(timeout[1]), '%Y-%m-%d %H:%M:%S') + timedelta(minutes=timeout[2])
                    if member is not None:
                        e.add_field(
                            name='{0} ({0.id})'.format(member), 
                            value='Timed out until: {} (GMT)\nTimeout Time: {} minutes'.format(
                                time_until_timeout, 
                                str(timeout[2])), 
                                inline=False
                        )
                    elif user is not None:
                        e.add_field(
                            name='{0} ({0.id}) (left server)'.format(user), 
                            value='Timed out until: {} (GMT)\nTimeout Time: {} minutes'.format(
                                time_until_timeout, 
                                str(timeout[2])), 
                                inline=False
                        )
                    else:
                        e.add_field(
                            name='Unknown User ({0})'.format(timeout[0]), 
                            value='Timed out until: {} (GMT)\nTimeout Time: {} minutes'.format(
                                time_until_timeout, 
                                str(timeout[2])), 
                                inline=False
                        )
            else:
                e.add_field(name='No timeouts on this page', value='-', inline=False)
        except Exception as e:
            await ctx.send(embed=await embeds.default_exception(e))
        else:
            await ctx.send(embed=e)

    @timeout.group(name='overview', invoke_without_command=True)
    async def timeout_overview(self, ctx, page: int=1):
        """Show an overview of people who have more than one timeout"""
        if ctx.invoked_subcommand is None:
            try:
                self.c.execute('SELECT MemberID, TimeoutTime, TimeoutCount '
                               'FROM timeouts '
                               'WHERE ServerID = ? '
                               'AND TimeoutCount > 0 '
                               'LIMIT 10 OFFSET ?', (ctx.message.guild.id, ((page - 1) * 10)))
                rows = self.c.fetchall()

                e = discord.Embed(title='Timeout Overview')
                e.set_footer(text='Page {}'.format(page))
                if len(rows) > 0:
                    for row in rows:
                        member = ctx.message.guild.get_member(int(row[0]))
                        user = self.bot.get_user(int(row[0]))
                        timeout_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                        if member is not None:
                            e.add_field(
                                name='{0} ({0.id})'.format(member), 
                                value='Total Timeouts: {}\nLast Timeout: {} (GMT)'.format(
                                    str(row[2]), 
                                    str(timeout_time)), 
                                    inline=False
                            )
                        elif user is not None:
                            e.add_field(
                                name='{0} ({0.id}) (left server)'.format(user), 
                                value='Total Timeouts: {}\nLast Timeout: {} (GMT)'.format(
                                    str(row[2]), 
                                    str(timeout_time)), 
                                    inline=False
                            )
                        else:
                            e.add_field(
                                name='Unknown User ({0})'.format(row[0]), 
                                value='Total Timeouts: {}\nLast Timeout: {} (GMT)'.format(
                                    str(row[2]), 
                                    str(timeout_time)), 
                                    inline=False
                            )
                else:
                    e.add_field(name='No timeouts on this page', value='-', inline=False)
            except Exception as e:
                await ctx.send(embed=await embeds.default_exception(e))
            else:
                await ctx.send(embed=e)

    @timeout_overview.command(name='user')
    async def overview_user(self, ctx, *, member: discord.Member=None):
        """Show an overview of people who have more than one timeout"""
        try:
            self.c.execute('SELECT MemberID, TimeoutTime, TimeoutCount '
                           'FROM timeouts WHERE ServerID = ? AND MemberID = ?', (ctx.message.guild.id, member.id))
            timeout = self.c.fetchone()
            if timeout is not None:
                timeout_time = datetime.strptime(timeout[1], '%Y-%m-%d %H:%M:%S')
                desc = 'Total Timeouts: {}\nLast Timeout: {}'.format(str(timeout[2]), str(timeout_time))
            else:
                desc = 'No timeouts for this user found on this server!'
        except AttributeError:
            await ctx.send(embed=discord.Embed(
                title='Error', 
                description='Incorrect usage of command.\n{}timeout overview user @MENTION'.format(PREFIX)))
        except Exception as e:
            await ctx.send(embed=await embeds.default_exception(e))
        else:
            e = discord.Embed(title='Timeout Overview: {}'.format(member), description=desc)
            await ctx.send(embed=e)

    @timeout.command(name='remove')
    async def timeout_remove(self, ctx, member: discord.Member):
        """Remove a timeout from a user

            - Sets Enabled to False in "timeouts" for a user
            - Removes "Blocked" role from the user
        """
        try:
            self.c.execute('SELECT ID FROM timeouts WHERE MemberID = ? AND ServerID = ?',
                           (member.id, ctx.message.guild.id))
            t_id = self.c.fetchone()[0]
            role = discord.utils.get(ctx.message.guild.roles, name='Blocked')
            if t_id >= 0:
                await member.remove_roles(role)
                self.c.execute('UPDATE timeouts SET Enabled = 0 WHERE ID = ?', [t_id])
            else:
                await ctx.send(embed=discord.Embed(title='Error', description='User was not timed out.'))
                return
        except Exception as e:
            await ctx.send(embed=await embeds.default_exception(e))
        else:
            self.connection.commit()
            await ctx.send(embed=discord.Embed(
                title='Timeout removed.', 
                description='Timeout from {} removed.'.format(member)
            ))

    @timeout.command(name='reset')
    async def timeout_reset(self, ctx, member: discord.Member):
        """Resets the timeout count for a user
           - only server side
           - removes the Blocked role!
        """
        try:
            if await self.user_exists(ctx, member.id) is True:
                self.c.execute('UPDATE timeouts SET TimeoutCount = 0, Enabled = 0 WHERE MemberID = ? AND ServerID = ?',
                               (member.id, ctx.message.guild.id))
                role = discord.utils.get(ctx.message.guild.roles, name='Blocked')
                await member.remove_roles(role)
            else:
                await ctx.send(embed=discord.Embed(
                    title='Error!',
                    description='User does not have any timeouts on this server!',
                    color=0xFF0000
                ))
                return
        except Exception as e:
            await ctx.send(embed=await embeds.default_exception(e))
        else:
            self.connection.commit()
            await ctx.send(embed=discord.Embed(
                title='Reset successful.', 
                description='Timeouts reset for {}.'.format(member)
            ))

    @timeout.command(name='user')
    async def timeout_user(self, ctx, member: discord.Member, amount: int, *, reason: str = 'None'):
        """Timeout a user you don't like

            - Adds the "Blocked" role to the user
            - Adds an entry to the "timeouts" table if not exists already
            - Adds one point to the global timeout count 
            - Adds one point to the server timeout count if user was timed out before
        """
        try:
            role = discord.utils.get(ctx.message.guild.roles, name='Blocked')
            if role:
                self.c.execute('SELECT TimeoutCount FROM timeouts WHERE MemberID = ? AND ServerID = ?',
                               (member.id, ctx.message.guild.id))
                result = self.c.fetchone()

                if result is None:
                    self.c.execute('SELECT MAX(ID) FROM timeouts')
                    max_id = self.c.fetchone()
                    next_id = 0 if max_id[0] is None else int(max_id[0]) + 1
                    self.c.execute('INSERT INTO timeouts  VALUES '
                                   '(?, ?, ?, ?, ?, 1, 1)',
                                   (next_id, ctx.message.guild.id, member.id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), amount))
                else:
                    self.c.execute('UPDATE timeouts '
                                   'SET TimeoutTime = ?, TimeInMinutes = ?, TimeoutCount = (? + 1), '
                                   'Enabled = 1 '
                                   'WHERE ServerID = ? AND MemberID = ?',
                                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), amount, result[0], ctx.message.guild.id, member.id))

                update ='UPDATE users SET TimeoutCount = ((SELECT TimeoutCount FROM users WHERE ID = ?) + 1) WHERE ID = ?'
                if await self.user_exists(ctx, member.id) is True:
                    self.c.execute(update, (member.id, member.id))
                else:
                    await self.add_user(ctx, member.id)
                    self.c.execute(update, (member.id, member.id))

                await member.add_roles(role)
            else:
                await ctx.send(embed=discord.Embed(
                    title='Role Error', 
                    description='Blocked role is missing on this server!'
                ))
        except Exception as e:
            await ctx.send(embed=await embeds.default_exception(e))
        else:
            self.connection.commit()
            await ctx.send(embed=discord.Embed(
                title='Timeout',
                description='User {0} is now silenced for {1} minutes'.format(member, amount)
            ))

            try:
                e = discord.Embed(
                    title='Timeout', 
                    description='You got timed out for **{}** minutes on {}!\n**Reason**: {}'.format(amount, ctx.message.guild, reason),
                    color=0xf4f142,
                    timestamp=datetime.now()
                )
                e.set_footer(text=ctx.message.author, icon_url=ctx.message.author.avatar_url)
                await member.send(embed=e)

                channelid = await self.get_activitylog_channel(ctx.message.guild.id)
                if channelid is not None:
                    channel = ctx.message.guild.get_channel(channelid)
                    e = discord.Embed(
                        title='Timeout', 
                        description='{} got timed out for **{}** minutes!\n**Reason**: {}'.format(member, amount, reason),
                        color=0xf4f142,
                        timestamp=datetime.now()
                    )
                    e.set_footer(text=ctx.message.author, icon_url=ctx.message.author.avatar_url)
                    await channel.send(embed=e)
            except discord.errors.NotFound as e:
                print('[error]Timeout activitylog channel: {}'.format(e))


    @commands.group()
    @checks.is_owner_guild()
    async def settings(self, ctx):
        """ Commands for guild owner"""
        if ctx.invoked_subcommand is None:
            pass

    @settings.command(name='fix')
    async def _fix(self, ctx):
        try:
            self.c.execute('INSERT INTO servers VALUES (?, ?, 0, 0, 1)', 
                          (ctx.message.guild.id, ctx.message.guild.name))
        except sqlite3.IntegrityError as e:
            await ctx.send(embed=discord.Embed(
                title='Done',
                description='Server **{0.name}** is already in the database.'.format(ctx.message.guild),
                color=0x00FF00
            ))
        except Exception as e:
            await ctx.send(embed=await embeds.default_exception(e))
        else:
            self.connection.commit()
            print('[database]Guild {0.name} : {0.id} added!'.format(ctx.message.guild))
            await ctx.send(embed=discord.Embed(
                title='Server readded',
                description='Server {0.name} readded to database.'.format(ctx.message.guild),
                color=0x00FF00
            ))

    @settings.group(name='activitylog')
    async def settings_activitylog(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @settings_activitylog.command(name='set')
    async def _activitylog_set(self, ctx):
        try:
            self.c.execute('UPDATE servers SET ActivityLogChannel = ? WHERE ID = ?', 
                          (ctx.message.channel.id, ctx.message.guild.id))
        except Exception as e:
            await ctx.send(embed=await embeds.default_exception(e))
        else:
            self.connection.commit()
            await ctx.send(embed=discord.Embed(
                title='Activity Log Channel',
                color=0xf4f142,
                description='Channel "{}" set to activity log channel!'.format(ctx.message.channel.name)
            ))

    @settings_activitylog.command(name='remove')
    async def _activitylog_remove(self, ctx):
        try:
            self.c.execute('UPDATE servers SET ActivityLogChannel = ? WHERE ID = ?', (0, ctx.message.guild.id))
        except Exception as e:
            print('[error]_activitylog_set: {}'.format(e))
        else:
            self.connection.commit()
            await ctx.send(embed=discord.Embed(
                title='Activity Log Channel',                                      
                color=0xf4f142,
                description='Activity log channel was removed from this server!'
            ))

    async def timeout_check(self):
        print('[bg] Timeout check active')
        while not self.bot.is_closed():
            async with self.timeout_lock:
                try:
                    self.c.execute('SELECT * FROM timeouts WHERE Enabled = 1')
                    timeouts = self.c.fetchall()
                    if len(timeouts) > 0:
                        for timeout in timeouts:
                            guild = self.bot.get_guild(int(timeout[1]))
                            if guild is None:
                                print('[ERR] timeout_check: server not found (ID: {})... Removing server entries...'.format(str(timeout[1])))
                                self.c.execute('DELETE FROM timeouts WHERE ServerID = ?', [timeout[1]])
                            else:
                                member = guild.get_member(int(timeout[2]))
                                if member is not None:
                                    role = discord.utils.get(guild.roles, name='Blocked')
                                    timeout_time = datetime.strptime(timeout[3], '%Y-%m-%d %H:%M:%S') + timedelta(minutes=timeout[4])
                                    print('[DEBUG][timeout-check] SERVER : {} | MEMBER : {}  | Timeout Time: {}'.format(guild, member, timeout_time))  # DEBUG
                                    if timeout_time <= datetime.now():
                                        await member.remove_roles(role)
                                        self.c.execute('UPDATE timeouts SET Enabled = 0 WHERE ID = ?', [timeout[0]])
                                    else:
                                        await member.add_roles(role)
                except Exception as e:
                    print('[error]timeout_check: {}'.format(e))
                finally:
                    self.connection.commit()
            print('[DEBUG] TIMEOUT CHECK : EVENT : LOOP COMPLETED (15 s)')
            await asyncio.sleep(15)

    async def add_user(self, ctx, user_id):
        try:
            self.c.execute('INSERT INTO users (ID) VALUES (?)', [user_id])
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e)))
        else:
            print('[database]ADDED USER : {}'.format(user_id))

    async def get_activitylog_channel(self, guildid):
        self.c.execute('SELECT ActivityLogChannel FROM servers WHERE ID = ?', [guildid])
        channel_id = self.c.fetchone()
        try:
            return channel_id[0]
        except:
            return None

    async def user_exists(self, ctx, user_id):
        try:
            self.c.execute('SELECT ID FROM users WHERE ID = ?', [user_id])
            try:
                if self.c.fetchone()[0] > 0:
                    return True
                else:
                    return False
            except:
                return False
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e)))


def setup(bot):
    bot.add_cog(Moderation(bot))
