import asyncio
import discord
import sqlite3

from datetime import datetime, timedelta
from discord.ext import commands
from ext.utils import checks
from settings import *


class Moderation:
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE)
        self.c = self.connection.cursor()

        self.timeout_check = bot.loop.create_task(self.timeout_check())

    @commands.command(pass_context=True)
    @checks.can_manage()
    async def prune(self, ctx, amount: int):
        await self.bot.purge_from(ctx.message.channel, limit=amount)

    @commands.group(pass_context=True)
    @checks.can_manage()
    async def timeout(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @timeout.command(pass_context=True, name='del')
    async def timeout_del(self, ctx, member: discord.Member):
        """Remove a timeout from a user
        
            - Removes entry from "timeouts" table
            - Removes "Blocked" role from the user            
        """
        try:
            self.c.execute('SELECT ID FROM timeouts '
                           'WHERE MemberID = {0.id} '
                           'AND ServerID = {1.message.server.id}'.format(member, ctx))
            t_id = self.c.fetchone()[0]
            role = discord.utils.get(ctx.message.server.roles, name='Blocked')
            if t_id > 0:
                await self.bot.remove_roles(member, role)
                self.c.execute('DELETE FROM timeouts WHERE ID = {}'.format(str(t_id)))
            else:
                await self.bot.say(embed=discord.Embed(title='Error', description='User was not timed out.'))
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e)))
        else:
            self.connection.commit()
            await self.bot.say(embed=discord.Embed(title='Timeout removed.', description=''.format()))

    @timeout.command(pass_context=True, name='list')
    async def timeout_list(self, ctx):
        """Lists all current timeouts for the server"""
        try:
            self.c.execute('SELECT MemberID, TimeoutTime, TimeInMinutes '
                           'FROM timeouts '
                           'WHERE ServerID = "{0.message.server.id}"'.format(ctx))
            timeouts = self.c.fetchall()
            desc = ''
            if len(timeouts) > 0:
                for timeout in timeouts:
                    member = ctx.message.server.get_member(user_id=str(timeout[0]))
                    time_until_timeout = datetime.strptime(str(timeout[1]), '%Y-%m-%d %H:%M:%S') + timedelta(hours=2, minutes=timeout[2])
                    self.c.execute('SELECT TimeoutCount FROM users WHERE ID = {}'.format(member.id))
                    try:
                        timeout_count = self.c.fetchone()[0]
                    except:
                        timeout_count = 0
                    desc += '{0} : {1} : {2}'.format(timeout_count, member, time_until_timeout)
            else:
                desc = 'No timeouts on this server.'
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e)))
        else:
            e = discord.Embed(title='Timeout List', description=desc)
            e.set_footer(text='Total timeouts : User : Time until timed out')
            await self.bot.say(embed=e)

    @timeout.command(pass_context=True, name='overview')
    async def timeout_overview(self, ctx):
        """Show an overview of people who have more than one timeout"""
        try:
            self.c.execute('')
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e)))

    @timeout.command(pass_context=True, name='user')
    async def timeout_user(self, ctx, member: discord.Member, amount: int):
        #  TODO: Check if user is already timed out on the same server
        """Timeout a user you don't like

            - Adds an entry to the "timeouts" table
            - Adds the "Blocked" role to the user
            - Adds one point to the timeout count in the "users" table
        """
        try:
            role = discord.utils.get(ctx.message.server.roles, name='Blocked')
            if role:
                await self.bot.add_roles(member, role)

                self.c.execute('SELECT MAX(ID) FROM timeouts')
                try:
                    t_id = self.c.fetchone()[0] + 1
                except:
                    t_id = 1

                self.c.execute('INSERT INTO timeouts  VALUES '
                               '({0}, {1.message.server.id}, {2.id}, CURRENT_TIMESTAMP, {3})'
                               .format(t_id, ctx, member, amount))

                if await self.user_exists(member.id) is True:
                    self.c.execute('UPDATE users '
                                   'SET TimeoutCount = ((SELECT TimeoutCount FROM users WHERE ID = {0}) + 1) '
                                   'WHERE ID = {0}'.format(member.id))
                else:
                    await self.add_user(member.id)
                    self.c.execute('UPDATE users '
                                   'SET TimeoutCount = ((SELECT TimeoutCount FROM users WHERE ID = {0}) + 1) '
                                   'WHERE ID = {0}'.format(member.id))
            else:
                await self.bot.say(embed=discord.Embed(title='Role Error', description='Blocked role is missing!'))
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e)))
        else:
            self.connection.commit()
            await self.bot.say(embed=discord.Embed(title='Timeout', description='User {0} is now silenced for {1} minutes'.format(member, amount)))

    @commands.group(pass_context=True, hidden=True)
    @checks.is_owner_server()
    async def mod(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @mod.command(pass_context=True, name='add')
    async def mod_add(self, ctx, *, member: discord.Member):
        """Adds a bot-moderator for a specific server"""
        try:
            self.c.execute('INSERT INTO moderators VALUES'
                           '({0.id}, {1.message.server.id}, 0)'.format(member, ctx))
        except sqlite3.IntegrityError:
            await self.bot.say(embed=discord.Embed(title='Error', description='User is already a mod on this server!', color=0xFF0000))
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error: Could not add mod', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.bot.say(embed=discord.Embed(title='Mod added!', description='{0.name} : {0.id}'.format(member)))

    @mod.command(pass_context=True, name='list')
    async def mod_list(self, ctx):
        """Shows all bot-moderators for the specific server"""
        try:
            self.c.execute('SELECT ID FROM moderators WHERE ServerID = {0.message.server.id}'.format(ctx))
            mods = self.c.fetchall()
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e)))
        else:
            desc = ''
            for mod in mods:
                desc += '**{0}** : {0.id}\n'.format(ctx.message.server.get_member(user_id=str(mod[0])))
            await self.bot.say(embed=discord.Embed(title='Server Moderators', description=desc))

    @mod.command(pass_context=True, name='remove')
    async def mod_remove(self, ctx, *, member: discord.Member):
        """Removes a bot-moderator for a specific server

           - can't remove the server owner
        """
        if not member.id == ctx.message.server.owner.id:
            try:
                self.c.execute('DELETE FROM moderators WHERE ServerID = {0.message.server.id} AND ID = {1.id}'.format(ctx, member))
            except Exception as e:
                await self.bot.say(
                    embed=discord.Embed(title='Error: Could not add mod', description=str(e), color=0xFF0000))
            else:
                await self.bot.say(
                    embed=discord.Embed(title='Mod removed!', description='{0.name} : {0.id}'.format(member)))
                self.connection.commit()
        else:
            await self.bot.say(embed=discord.Embed(title='Error: Cannot remove server owner!', color=0xFF0000))

    @asyncio.coroutine
    async def timeout_check(self):
        while not self.bot.is_closed:
            try:
                self.c.execute('SELECT * FROM timeouts')
                timeouts = self.c.fetchall()
            except Exception as e:
                print('[error]timeout_check: {}'.format(str(e)))
            else:
                if len(timeouts) > 0:
                    for timeout in timeouts:
                        server = self.bot.get_server(id=str(timeout[1]))
                        member = server.get_member(user_id=str(timeout[2]))
                        role = discord.utils.get(server.roles, name='Blocked')
                        timeout_time = datetime.strptime(timeout[3], '%Y-%m-%d %H:%M:%S') + timedelta(minutes=timeout[4], hours=2)
                        if timeout_time <= datetime.now():
                            await self.bot.remove_roles(member, role)
                            self.c.execute('DELETE FROM timeouts WHERE ID = {}'.format(str(timeout[0])))
            finally:
                self.connection.commit()
            await asyncio.sleep(15)

    async def add_user(self, user_id):
        try:
            self.c.execute('INSERT INTO users (ID) VALUES ({0})'.format(user_id))
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e)))
        else:
            print('[database]ADDED USER : {}'.format(user_id))

    async def user_exists(self, user_id):
        try:
            self.c.execute('SELECT ID FROM users WHERE ID = {}'.format(user_id))
            try:
                if self.c.fetchone()[0] > 0:
                    return True
                else:
                    return False
            except:
                return False
        except Exception as e:
            await self.bot.say(embed=discord.Embed(title='Error', description=str(e)))


def setup(bot):
    bot.add_cog(Moderation(bot))
