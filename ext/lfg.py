import asyncio
import discord
import sqlite3

from discord.ext import commands
from ext.utils import checks
from settings import *

class LFG:
    """LFG - Looking For Group
       
       Look for groups through this module
        - adds LFG role if looking for group
    """
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE)
        self.c = self.connection.cursor()

    @commands.group(invoke_without_command=True, case_insensitive=True)
    async def ready(self, ctx):
        if ctx.invoked_subcommand is None:
            self.c.execute('SELECT RoleID FROM lfg WHERE ServerID = ?', [ctx.message.guild.id])
            roleid = self.c.fetchone()

            if roleid is not None:
                role = discord.Object(id=roleid[0])
                if role is not None:
                    if any(str(x.id) == str(role.id) for x in ctx.message.author.roles):
                        for x in ctx.message.author.roles:
                            if str(x.id) == str(role.id):
                                role = discord.utils.get(ctx.message.guild.roles, name=x.name)

                        await ctx.author.remove_roles(role)
                        await ctx.send('{0} is not ready anymore!'.format(ctx.message.author.mention), delete_after=5.0)
                        await asyncio.sleep(5)
                        await ctx.message.delete()
                    else:
                        await ctx.author.add_roles(role)
                        await ctx.send('{0} is ready!'.format(ctx.message.author.mention), delete_after=5.0)
                        await asyncio.sleep(5)
                        await ctx.message.delete()
                else:
                    await ctx.send(
                        embed=discord.Embed(
                            title='Error: Role Change Detected',
                            description='Please set the role again. \nCommand: {}ready role [role name]'.format(PREFIX),
                            color=0xFF0000
                        )
                    )
            else:
                await ctx.send(
                    embed=discord.Embed(
                        title='Error: Role Not Found',
                        description='The role wasn\'t set on this guild yet. \nCommand: {}ready role [role name]'.format(PREFIX),
                        color=0xFF0000
                    )
                )

    @ready.command(name='role')
    @checks.can_manage()
    async def _set_role(self, ctx, *, query=None):
        role = None  # TODO: Role mention and role id

        if role is None:
            role = discord.utils.get(ctx.message.guild.roles, name=query)
        
        if role is not None:
            self.c.execute('SELECT RoleID FROM lfg WHERE RoleID = ? AND ServerID = ?', (
                role.id, 
                ctx.message.guild.id
            ))
            db_role = self.c.fetchone()

            if db_role is None:
                self.c.execute('INSERT INTO lfg VALUES (?, ?)', (
                    role.id, 
                    ctx.message.guild.id
                ))
            else:
                self.c.execute('UPDATE lfg SET RoleID = ? WHERE RoleID = ? AND ServerID = ?', (
                    role.id, 
                    db_role[0], 
                    ctx.message.guild.id
                ))
            
            self.connection.commit()

            await ctx.send(
                embed=discord.Embed(
                    title='Role set',
                    description='Role **{}** set as LFG role!'.format(role.name),
                    color=0x00d8ff
                )
            )

        else:
            await ctx.send(
                embed=discord.Embed(
                    title='Error: Role Not Found',
                    description='The bot couldn\'t find the role.',
                    color=0xFF0000
                )
            )

def setup(bot):
    bot.add_cog(LFG(bot))
