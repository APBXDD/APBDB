import aiohttp
import asyncio
import discord
import sqlite3
import os
import re
import math  # WutFace

from datetime import datetime, timedelta
from discord.ext import commands
from ext.utils import checks
from settings import *

ext = True
try:
    from twitch import TwitchClient
except ImportError:
    ext = False


class Twitch:
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE)
        self.c = self.connection.cursor()

        self.twitchClient = TwitchClient(client_id=TWITCH_ID)

        self.notifier_task = bot.loop.create_task(self.twitch_notify())
        self.notifier_task_lock = asyncio.Lock()

    def __del__(self):
        self.notifier_task.cancel()

    TWITCH_API = 'https://api.twitch.tv/kraken'
    TWITCH_LOGO = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTURYDhGkbONkCqAOExibcLSvxdjCoWZtV8G24El4Y7YU7MKuZc'

    @commands.group()
    @checks.can_manage()
    async def twitch(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @twitch.command(name='add', no_pm=True)
    async def _twitch_add(self, ctx, *, userq: str):
        userqs = userq.split(',')
        for userq in userqs:
            await ctx.trigger_typing()
            user = await self.user_exists(userq)
            if user is not False:
                self.c.execute('SELECT COUNT(*) FROM twitch WHERE ServerID = ? AND UserID = ?', (
                    ctx.message.guild.id, 
                    user.id
                ))
                if int(self.c.fetchone()[0]) > 0:
                    await self.twitch_e(ctx, 'Channel {} already in the notification list!'.format(
                        user.display_name
                    ))
                else:
                    try:
                        self.c.execute('INSERT INTO twitch(UserID, ServerID) VALUES (?, ?)', (
                            user.id,
                            ctx.message.guild.id
                        ))
                        await self.twitch_e(
                            ctx, 
                            'Channel added!', 
                            '**{}** added to notification list.'.format(user.display_name)
                        )
                    except Exception as e:
                        await ctx.send(embed=discord.Embed(title='Error', description=str(e)))
                    else:
                        self.connection.commit()
            else:
                await self.twitch_e(
                    ctx, 
                    'Channel not found.',
                    '**{}** wasn\'t found or doesn\'t exist!'.format(userq)
                )

    @twitch.command(name='list', no_pm=True)
    async def _twitch_list(self, ctx, *, page: int = None):
        try:
            await ctx.trigger_typing()
            users = self.c.execute('SELECT UserID FROM twitch WHERE ServerID = ?', [ctx.message.guild.id]).fetchall()
            per_embed = 10
            page = 1 if page is None or page < 1 or page > math.ceil(len(users) / per_embed) else page 

            e = discord.Embed(title='Twitch Channels', color=0x6441A5)
            e.set_author(name='Twitch Alert', icon_url=self.TWITCH_LOGO)
            e.set_footer(
                text='Page {} of {} | {} Channels'.format(
                        page,
                        math.ceil(len(users) / per_embed),
                        len(users)
                    ), 
                icon_url=self.TWITCH_LOGO)
            message = await ctx.send(embed=e)
            for user in users[(0 + (per_embed * (page - 1))):(per_embed + (per_embed * (page - 1)))]:
                await ctx.trigger_typing()
                channel = self.twitchClient.channels.get_by_id(user[0])
                stream = self.twitchClient.streams.get_stream_by_user(channel.id)
                e.add_field(
                    name=channel.display_name, 
                    value='{}'.format(
                        await self.channel_online(stream)
                    )
                )
                await message.edit(embed=e)
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e)))

    @twitch.command(name='remove', no_pm=True)
    async def _twitch_remove(self, ctx, *, user: str):
        user = await self.user_exists(user)
        if user is not False:
            self.c.execute('SELECT COUNT(*) FROM twitch WHERE ServerID = ? AND UserID = ?', (
                ctx.message.guild.id, 
                user.id
            ))
            if int(self.c.fetchone()[0]) > 0:
                try:
                    self.c.execute('DELETE FROM twitch WHERE ServerID = ? AND UserID = ?', (
                        ctx.message.guild.id,
                        user.id
                    ))
                    await self.twitch_e(
                        ctx, 
                        'Channel removed!',
                        '**{}** removed from notification list.'.format(user.display_name))
                except Exception as e:
                    await ctx.send(embed=discord.Embed(title='Error', description=str(e)))
                else:
                    self.connection.commit()
            else:
                await self.twitch_e(ctx, 'Channel {} is not in the notification list!'.format(
                    user.display_name
                ))            
        else:
            await self.twitch_e(
                ctx, 
                'Channel not found.',
                '**{}** wasn\'t found or doesn\'t exists!'.format(user)
            )

    @twitch.group(name='channel')
    async def twitch_channel(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @twitch_channel.command(name='set', no_pm=True)
    async def _channel_set(self, ctx):
        try:
            self.c.execute('UPDATE servers SET TwitchChannel = ? WHERE ID = ?',
                           (ctx.message.channel.id, ctx.message.guild.id))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e)))
        else:
            self.connection.commit()
            await self.twitch_e(ctx, 'Notification channel set.',
                                'Discord channel "{}" set as notification channel!'.format(ctx.message.channel.name))

    @twitch_channel.command(name='remove', no_pm=True)
    async def _channel_remove(self, ctx):
        try:
            self.c.execute('UPDATE servers SET TwitchChannel = 0 WHERE ID = ?', [ctx.message.guild.id])
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e)))
        else:
            self.connection.commit()
            await self.twitch_e(ctx, 'Notification channel removed.')

    async def twitch_notify(self):
        print('[bg] Twitch Notify active.')
        while not self.bot.is_closed():
            async with self.notifier_task_lock:
                self.c.execute('SELECT * FROM servers')
                guilds = self.c.fetchall()
                for guild in guilds:
                    srv = self.bot.get_guild(int(guild[0]))
                    if guild[2] is not 0:
                        try:
                            self.c.execute('SELECT UserID FROM twitch WHERE ServerID = ?', [srv.id])
                            users = self.c.fetchall()
                            for user in users:
                                stream = self.twitchClient.streams.get_stream_by_user(user)
                                if stream is not None:
                                    if await self.twitch_notify_update(srv.id, stream) is True:
                                        await self.twitch_notify_message(stream, guild[2])
                        except Exception as e:
                            print(e)
            print('[DEBUG] TWITCH NOTIFY : EVENT : LOOP COMPLETED (120 s)')
            await asyncio.sleep(120)

    async def twitch_notify_update(self, server_id, stream):    
        if stream.stream_type == 'live':
            if stream.created_at < datetime.now():
                self.c.execute('SELECT LastStream FROM twitch WHERE UserID = ? AND ServerID = ?', (
                    stream.channel.id, 
                    server_id
                ))
                last_stream = self.c.fetchone()
                last_stream = last_stream[0]
                if last_stream is None:
                    self.c.execute('UPDATE twitch SET LastStream = ? WHERE ServerID = ? AND UserID = ?', (
                        stream.created_at,
                        server_id,
                        stream.channel.id
                    ))
                    self.connection.commit()
                    return True
                elif datetime.strptime(last_stream, '%Y-%m-%d %H:%M:%S') + timedelta(minutes=10) < stream.created_at:
                    self.c.execute('UPDATE twitch SET LastStream = ? WHERE ServerID = ? AND UserID = ?', (
                        stream.created_at,
                        server_id,
                        stream.channel.id, 
                    ))
                    self.connection.commit()
                    return True
                elif datetime.strptime(last_stream, '%Y-%m-%d %H:%M:%S') + timedelta(minutes=10) > stream.created_at:
                    self.c.execute('UPDATE twitch SET LastStream = ? WHERE ServerID = ? AND UserID = ?', (
                        datetime.strptime(last_stream, '%Y-%m-%d %H:%M:%S') + timedelta(minutes=10),
                        server_id,
                        stream.channel.id, 
                    ))
                    self.connection.commit()
        return False

    async def twitch_notify_message(self, stream, channel_id):
        try:
            channel = self.bot.get_channel(int(channel_id))
            e = discord.Embed(
                title='Now Live: {}'.format(stream.channel.display_name),
                description=await self.twitch_filter(stream.channel.status),
                url=stream.channel.url,
                timestamp=stream.created_at,
                color=0x6441A5
            )
            e.set_author(name='Twitch Alert', icon_url=self.TWITCH_LOGO)
            e.set_thumbnail(url=stream.channel.logo)
            e.add_field(name='Playing', value=stream.game)
            e.set_footer(text='Stream started')
            await channel.send(embed=e)
        except Exception as e:
            print('[Error]twitch_notify_message: {}'.format(e))

    async def twitch_e(self, ctx, title, description=None):
        channel = self.bot.get_channel(ctx.message.channel.id)
        post = discord.Embed(
            title=title, 
            description=description,
            color=0x6441A5
        )
        post.set_author(name='Twitch Alert', icon_url=self.TWITCH_LOGO)
        await channel.send(embed=post)

    async def twitch_filter(self, text):
        text = re.sub(r'http\S+', ' <link removed> ', text)
        text = re.sub(r'https\S+', ' <link removed> ', text)
        return text

    async def user_exists(self, user):
        try:
            user = self.twitchClient.users.translate_usernames_to_ids(user)[0]
            return user
        except IndexError:
            return False
        
    async def channel_online(self, stream):
        try:
            if stream is None:
                return 'Offline'
            elif stream.stream_type == 'live':
                return '\N{VIDEO GAME} [Live]({})'.format(stream.channel.url)
            elif stream.stream_type == 'rerun':
                return '\N{MOVIE CAMERA} [Vodcast]({})'.format(stream.channel.url)
        except:
            return 'Unknown'
        return 'Unknown'


def setup(bot):
    if ext is True:
        bot.add_cog(Twitch(bot))
    else:
        print('[exts]Extension "twitch" not loaded. Missing python-twitch-client! (pip install python-twitch-client)')
        raise ImportError
