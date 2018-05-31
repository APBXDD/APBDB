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
from ext.utils.utils import Message
from settings import *


class Twitch:
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE)
        self.c = self.connection.cursor()

        self.notifier_task = bot.loop.create_task(self.twitch_notify())
        self.notifier_task_lock = asyncio.Lock()

    def __del__(self):
        self.notifier_task.cancel()

    TWITCH_API = 'https://api.twitch.tv/kraken'
    TWITCH_LOGO = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTURYDhGkbONkCqAOExibcLSvxdjCoWZtV8G24El4Y7YU7MKuZc'

    @commands.group(case_insensitive=True)
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
                    user['_id']
                ))
                if int(self.c.fetchone()[0]) > 0:
                    await self.twitch_e(ctx, 'Channel {} already in the notification list!'.format(
                        user['display_name']
                    ))
                else:
                    try:
                        self.c.execute('INSERT INTO twitch(UserID, ServerID) VALUES (?, ?)', (
                            user['_id'],
                            ctx.message.guild.id
                        ))
                        await self.twitch_e(
                            ctx, 
                            'Channel added!', 
                            '**{}** added to notification list.'.format(user['display_name'])
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
                channel = await self.get_channel_by_id(user[0])
                stream = await self.get_stream(channel['_id'])
                e.add_field(
                    name=channel['display_name'], 
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
                user['_id']
            ))
            if int(self.c.fetchone()[0]) > 0:
                try:
                    self.c.execute('DELETE FROM twitch WHERE ServerID = ? AND UserID = ?', (
                        ctx.message.guild.id,
                        user['_id']
                    ))
                    await self.twitch_e(
                        ctx, 
                        'Channel removed!',
                        '**{}** removed from notification list.'.format(user['display_name']))
                except Exception as e:
                    await ctx.send(embed=discord.Embed(title='Error', description=str(e)))
                else:
                    self.connection.commit()
            else:
                await self.twitch_e(ctx, 'Channel {} is not in the notification list!'.format(
                    user['display_name']
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
        Message(1, "[TWITCH] Notifier loop active")
        while not self.bot.is_closed():
            Message(1, "[TWITCH] Notifier loop starting")
            async with self.notifier_task_lock:
                self.c.execute('SELECT * FROM servers')
                guilds = self.c.fetchall()
                for guild in guilds:
                    srv = self.bot.get_guild(int(guild[0]))
                    if guild[2] is not 0:
                        try:
                            Message(1, "[TWITCH] Guild {0} found.".format(srv))
                            self.c.execute('SELECT UserID FROM twitch WHERE ServerID = ?', [srv.id])
                            users = self.c.fetchall()
                            Message(1, "[TWITCH] Found {0} channels in guild {1}.".format(len(users), srv))
                            for user in users:
                                stream = await self.get_stream(user[0])
                                if stream != None:
                                    if await self.twitch_notify_update(srv.id, stream) is True:
                                        Message(1, "[TWITCH] Stream {0} live. Broadcasting...".format(stream['channel']['display_name']))
                                        await self.twitch_notify_message(stream, guild[2])
                        except Exception as e:
                            print(e)
            Message(1, "[TWITCH] Notifier loop completed (120 s)")
            await asyncio.sleep(120)

    async def translate_username_to_id(self, user):
        url = '{0}/users?login={1}'.format(self.TWITCH_API, user)
        user = await self._twitch_request(url)
        return user['users']

    async def get_stream(self, user_id):
        url = '{0}/streams/{1}'.format(self.TWITCH_API, user_id)
        stream = await self._twitch_request(url)
        return stream['stream']

    async def get_channel_by_id(self, channel_id):
        url ='{0}/channels/{1}'.format(self.TWITCH_API, channel_id)
        channel = await self._twitch_request(url)
        return channel

    async def _twitch_request(self, url, params = None):
        if params is None:
            params = {
                'Accept': 'application/vnd.twitchtv.v5+json',
                'Client-ID': TWITCH_ID
            }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=params) as r:
                if r.status == 200:
                    return await r.json()
        return r.status

    async def twitch_notify_update(self, server_id, stream):    
        if stream['stream_type'] == 'live':
            stream['created_at'] = datetime.strptime(stream['created_at'], '%Y-%m-%dT%H:%M:%SZ')

            if stream['created_at'] < datetime.now():
                self.c.execute('SELECT LastStream FROM twitch WHERE UserID = ? AND ServerID = ?', (
                    stream['channel']['_id'],
                    server_id
                ))
                last_stream = self.c.fetchone()
                last_stream = last_stream[0]
                if last_stream is None:
                    self.c.execute('UPDATE twitch SET LastStream = ? WHERE ServerID = ? AND UserID = ?', (
                        stream['created_at'],
                        server_id,
                        stream['channel']['_id']
                    ))
                    self.connection.commit()
                    return True
                elif datetime.strptime(last_stream, '%Y-%m-%d %H:%M:%S') + timedelta(minutes=10) < stream['created_at']:
                    self.c.execute('UPDATE twitch SET LastStream = ? WHERE ServerID = ? AND UserID = ?', (
                        stream['created_at'],
                        server_id,
                        stream['channel']['_id'], 
                    ))
                    self.connection.commit()
                    return True
                elif datetime.strptime(last_stream, '%Y-%m-%d %H:%M:%S') + timedelta(minutes=10) > stream['created_at']:
                    self.c.execute('UPDATE twitch SET LastStream = ? WHERE ServerID = ? AND UserID = ?', (
                        datetime.strptime(last_stream, '%Y-%m-%d %H:%M:%S') + timedelta(minutes=10),
                        server_id,
                        stream['channel']['_id'], 
                    ))
                    self.connection.commit()
        return False

    async def twitch_notify_message(self, stream, channel_id):
        try:
            channel = self.bot.get_channel(int(channel_id))
            e = discord.Embed(
                title='Now Live: {}'.format(stream['channel']['display_name']),
                description=await self.twitch_filter(stream['channel']['status']),
                url=stream['channel']['url'],
                timestamp=stream['created_at'],
                color=0x6441A5
            )
            e.set_author(name='Twitch Alert', icon_url=self.TWITCH_LOGO)
            e.set_thumbnail(url=stream['channel']['logo'])
            e.add_field(name='Playing', value=stream['game'])
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
            user = await self.translate_username_to_id(user)
            return user[0]
        except IndexError:
            return False
        
    async def channel_online(self, stream):
        try:
            if stream is None:
                return 'Offline'
            elif stream['stream_type'] == 'live':
                return '\N{VIDEO GAME} [Live]({})'.format(stream['channel']['url'])
            elif stream['stream_type'] == 'rerun':
                return '\N{MOVIE CAMERA} [Vodcast]({})'.format(stream['channel']['url'])
        except:
            return 'Unknown'
        return 'Unknown'


def setup(bot):
    bot.add_cog(Twitch(bot))
