import aiohttp
import asyncio
import discord
import re
import sqlite3
import threading

from bs4 import BeautifulSoup
from datetime import datetime
from discord.ext import commands
from ext.utils import utils, checks
from settings import *
from ext.utils.utils import Message


class APBDB2:
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE, isolation_level=None)
        self.c = self.connection.cursor()

        self.news_feed_lock = asyncio.Lock()
        self.news_feed = bot.loop.create_task(self.news_feed())

        self.version_feed_lock = asyncio.Lock()
        self.version_feed = bot.loop.create_task(self.version_feed())

    def __del__(self):
        self.news_feed.cancel()

    API_URL = 'https://db.apbvault.net/beacon/'

    @commands.command(name='db')
    async def db(self, ctx, *, query: str):
        await ctx.trigger_typing()

        detail = False
        if '-detail' in query:
            detail = True
            query = query.replace('-detail', '')

        #search = await self.weapon_search(query)
        #if search[0] is False: search = await self.item_search(query)
        search = await self.item_search(query)
        if search[0] is True:
            item = await utils.api_request(self.API_URL + 'items/{}'.format(search[1]['sapbdb']))
            try:
                description = str(item['item_detail']['sdescription'])
            except:
                description = None
            e = discord.Embed(
                title=str(item['item_detail']['sdisplayname']),
                description=description,
                url=str(item['url']),
                color=0xFF0000
            )
            if item['Category'] == 'Modifications':
                for effect in item['ModifierEffects']:
                    value = '**Multiplier:** {}  \n**Add:** {}'.format(
                        str(effect['feffectmultiplier']), 
                        str(effect['faddtoresult'])
                    )
                    e.add_field(name=await self.rem_color_code(str(effect['sdescription'])), value=value)
            elif item['Category'] == 'Vehicles':
                e.add_field(name='Max Health', value='{} '.format(item['VehicleSetupType']['nmaxhealth']))
                e.add_field(name='Max Speed', value='{} m/s'.format(item['VehicleSetupType']['fmaxspeed']))
                e.add_field(name='Max Reverse Speed', value='{} m/s'.format(item['VehicleSetupType']['fmaxreversespeed']))
                e.add_field(name='Max Explosion Damage', value='{} at {} cm'.format(
                    item['Explosions']['ndamage'], 
                    round(item['Explosions']['fgroundzeroradius'], 0))
                )
                e.add_field(name='Cargo Capacity', value='{}'.format(item['VehicleSetupType']['nmaincargopipcapacity']))
                e.add_field(name='Drive Type', value=await self.drive_type(item['VehicleSetupType']['edrivetype']))
            elif item['Category'] == 'Weapons':
                try:
                    e.add_field(name='TTK / STK', value='{} sec / {}'.format(
                        round(item['calculated']['timetokill_effect'], 2), 
                        item['calculated']['shottokill_effect'])
                    )
                    e.add_field(name='TTS / STS', value='{} sec / {}'.format(
                        round(item['calculated']['timetostun_effect'], 2), 
                        item['calculated']['shottostun_effect'])
                    )
                except:
                    e.add_field(name='TTK / STK', value='{} sec / {}'.format(
                        round(item['calculated']['timetokill'], 2), 
                        item['calculated']['shottokill'])
                    )
                    e.add_field(name='TTS / STS', value='{} sec / {}'.format(
                        round(item['calculated']['timetostun'], 2), 
                        item['calculated']['shottostun'])
                    )
                
                if detail is True:
                    e.add_field(
                        name='DMG / STM / HRD', 
                        value='{} / {} / {}'.format(
                            item['WeaponType']['fhealthdamage'], 
                            item['WeaponType']['fstaminadamage'], 
                            round((item['WeaponType']['fharddamagemodifier'] * item['WeaponType']['fhealthdamage']), 2))
                    )
                    e.add_field(
                        name='MAG / POOL',
                        value='{} / {}'.format(
                            item['WeaponType']['nmagazinecapacity'],
                            item['WeaponType']['nammopoolcapacity']),
                    )
            e.set_thumbnail(url=str(item['icon_url']))
            await ctx.send(embed=e)
        else:
            await ctx.send(embed=discord.Embed(
                title='Error', 
                description='Item not found. Your query: "{}"'.format(query), 
                color=0xFF0000)
            )

    @commands.group(name='apb')
    async def apb(self, ctx):
        if ctx.invoked_subcommand is None:
           pass 

    @apb.group(name='feed', no_pm=True)
    @checks.can_manage()
    @commands.guild_only()
    async def apb_feed(self, ctx):
        if ctx.invoked_subcommand is None:
           pass 

    @apb_feed.command(name='mod', no_pm=True)
    async def feed_mod(self, ctx, *, mods: bool):
        try:
            if mods is True:
                self.c.execute('UPDATE apb_news_feed SET ShowMods = 1 WHERE ID = ?', [ctx.message.guild.id])
                desc = 'Enabled moderators in news feed.'
            else:
                self.c.execute('UPDATE apb_news_feed SET ShowMods = 0 WHERE ID = ?', [ctx.message.guild.id])
                desc = 'Disabled moderators in news feed.'
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.apb_e(ctx, 'News Feed', description=desc)

    @apb_feed.command(name='set', no_pm=True)
    async def feed_set(self, ctx, *, post: int):
        try:
            self.c.execute('UPDATE apb_news_feed SET PostID = ? WHERE ID = ?', (post, ctx.message.guild.id))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.apb_e(ctx, 'News Feed', description='ID set to {}.'.format(post))

    @apb_feed.group(name='channel', no_pm=True)
    async def feed_channel(self, ctx):
        if ctx.invoked_subcommand is None:
           pass

    @feed_channel.command(name='remove', no_pm=True)
    async def channel_remove(self, ctx):
        try:
            self.c.execute('DELETE FROM apb_news_feed WHERE ID = ?', [ctx.message.guild.id])
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.apb_e(ctx, 'News Feed', 'Channel removed from this server.')

    @feed_channel.command(name='set', no_pm=True)
    async def channel_set(self, ctx):
        try:
            id = await utils.api_request(self.API_URL + 'tracker?limit=1')
            self.c.execute('INSERT INTO apb_news_feed VALUES (?, ?, ?, ?)', 
                          (ctx.message.guild.id, ctx.message.channel.id, id[0]['id'], 1))
        except sqlite3.IntegrityError as e:
            self.c.execute('UPDATE apb_news_feed SET ChannelID = ? WHERE ID = ?', (
                ctx.message.channel.id, 
                ctx.message.guild.id)
            )
            self.connection.commit()
            await self.apb_e(ctx, 'News Feed', 'Channel updated.')
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.apb_e(ctx, 'News Feed', 'Channel set.')

    @apb.group(name='version', no_pm=True)
    @checks.can_manage()
    @commands.guild_only()
    async def apb_version(self, ctx):
        if ctx.invoked_subcommand is None:
           pass 

    @apb_version.command(name='reset', no_pm=True)
    async def version_feed_reset(self, ctx):
        try:
            self.c.execute('UPDATE apb_version_feed SET VersionLive = NULL, VersionOTW = NULL, VersionOTW2 = NULL WHERE ID = ?', [ctx.message.guild.id])
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.apb_e(ctx, 'Version Feed', description='Versions reset')

    @apb_version.group(name='channel', no_pm=True)
    async def version_feed_channel(self, ctx):
        if ctx.invoked_subcommand is None:
           pass

    @version_feed_channel.command(name='remove', no_pm=True)
    async def version_channel_remove(self, ctx):
        try:
            self.c.execute('DELETE FROM apb_version_feed WHERE ID = ?', [ctx.message.guild.id])
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.apb_e(ctx, 'Version Feed', 'Channel removed from this server.')

    @version_feed_channel.command(name='set', no_pm=True)
    async def version_channel_set(self, ctx):
        try:
            version = await utils.api_request(self.API_URL + 'version')
            self.c.execute('INSERT INTO apb_version_feed VALUES (?, ?, ?, ?, ?)', 
                          (ctx.message.guild.id, ctx.message.channel.id, version['live'], version['otw'], version['otw2']))
        except sqlite3.IntegrityError as e:
            self.c.execute('UPDATE apb_version_feed SET ChannelID = ? WHERE ID = ?', (
                ctx.message.channel.id, 
                ctx.message.guild.id
                )
            )
            self.connection.commit()
            await self.apb_e(ctx, 'Version Feed', 'Channel updated.')
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.apb_e(ctx, 'Version Feed', 'Channel set.')

    @commands.command(name='role', no_pm=True)
    @commands.guild_only()
    async def role(self, ctx, *, role: str):
        roles = ['Citadel', 'Jericho', 'Han', 'Nekrova', 'Xbox One', 'PlayStation 4']
        if role.lower() == 'citadel':
            role = discord.utils.get(ctx.message.guild.roles, name='Citadel')
            await self.manage_role(ctx, role)
        elif role.lower() == 'jericho':
            role = discord.utils.get(ctx.message.guild.roles, name='Jericho')
            await self.manage_role(ctx, role)
        elif role.lower() == 'nekrova':
            role = discord.utils.get(ctx.message.guild.roles, name='Nekrova')
            await self.manage_role(ctx, role)
        elif role.lower() == 'xbox one' or role.lower() == 'xbone':
            role = discord.utils.get(ctx.message.guild.roles, name='Xbox One')
            await self.manage_role(ctx, role)
        elif role.lower() == 'playstation 4' or role.lower() == 'ps4':
            role = discord.utils.get(ctx.message.guild.roles, name='PlayStation 4')
            await self.manage_role(ctx, role)

    async def manage_role(self, ctx, role):
        if role:
            if any(role == rol for rol in ctx.message.author.roles):
                await ctx.message.author.remove_roles(role)
                await ctx.send('Removed {} role from {}.'.format(role, ctx.message.author))
            else:
                await ctx.message.author.add_roles(role)
                await ctx.send('Added {} role to {}.'.format(role, ctx.message.author))
        else:
            await ctx.send('Error: {} role not found.'.format(role))
    
    async def version_feed(self):
        Message(2, '[VERSIONFEED] Version Feed Task active')
        while not self.bot.is_closed():
            async with self.version_feed_lock:
                self.c.execute('SELECT * FROM apb_version_feed')
                servers = self.c.fetchall()
                versions = await utils.api_request(self.API_URL + 'version')
                for server in servers:
                    try:
                        live_version = server[2]
                        otw_version = server[3]
                        otw2_version = server[4]

                        if await self.version_feed_check(live_version, versions['live']):
                            await self.version_feed_update(versions['live'], 'live', server)

                        if await self.version_feed_check(otw_version, versions['otw']):
                            await self.version_feed_update(versions['otw'], 'otw', server)

                        if await self.version_feed_check(otw2_version, versions['otw2']):
                            await self.version_feed_update(versions['otw2'], 'otw2', server)
                    except Exception as e:
                        Message(3, "[VERSIONFEED] {0}".format(e))

            Message(1, '[VERSIONFEED] LOOP COMPLETED (60 s)')
            await asyncio.sleep(60)

    async def version_feed_check(self, version, new_version):
        if version is None:
            return True
        elif str(new_version) > str(version):
            return True
        return False

    async def version_feed_update(self, version, patch_server, server):
        try:
            self.c.execute('UPDATE apb_version_feed SET Version{0} = "{1}" WHERE ID = {2}'.format(
                patch_server, 
                version, 
                server[0])
            )
            
            e = discord.Embed(
                title='{0} Client Update'.format(patch_server.upper()), 
                description='Client version updated to {0}'.format(version), 
                color=0xFF0000,
                timestamp=datetime.now()
            )
            channel = self.bot.get_channel(int(server[1]))
        except Exception as e:
            Message(3, "[VERSIONFEED]".format(e))
        else:
            self.connection.commit()
            await channel.send(embed=e)

    async def news_feed(self):
        Message(2, '[NEWSFEED] APB News Feed active')
        while not self.bot.is_closed():
            self.c.execute('SELECT ID, ChannelID, PostID, ShowMods FROM apb_news_feed')
            servers = self.c.fetchall()
            Message(1, "[NEWSFEED] Checking {0} guilds".format(len(servers)))
            
            for server in servers:
                Message(1, "[NEWSFEED] Trying to get guild with ID {}.".format(int(server[0])))
                guild = self.bot.get_guild(int(server[0]))
                if guild is None:
                    Message(3, "[NEWSFEED] Guild {} not found.".format(server[0]))
                    continue
                if int(server[1]) is not 0:
                    Message(1, "[NEWSFEED][{1}] Getting channel: {0} ".format(server[1], guild))
                    try:
                        channel = guild.get_channel(int(server[1]))
                    except discord.NotFound:
                        continue
                    if channel is None:
                        Message(3, "[NEWSFEED][{0}] Could not get channel.".format(guild))
                        continue
                else:
                    continue
                Message(1, "[NEWSFEED][{0}] Channel found: {1}".format(guild, channel))
                postID = server[2]
                mods = server[3]
                if mods is 0:
                    request_url = self.API_URL + 'tracker?mod=False&currentid={}&limit=1000'.format(postID)
                else:
                    request_url = self.API_URL + 'tracker?currentid={}&limit=1000'.format(postID)
                Message(1, "[NEWSFEED][{0}] Attempting API request: {1}".format(guild, request_url))
                posts = []
                posts = await utils.api_request(request_url)
                try:
                    if posts > 200 and posts < 200:
                        Message(3, "[NEWSFEED]Request did not return JSON. Status: {}".format(posts))
                        continue
                except:
                    pass

                if len(posts) > 0 and not isinstance(posts, int):
                    Message(1, '[NEWSFEED][{0}] Processing {1} new posts'.format(guild, len(posts)))
                    for post in reversed(posts):
                        # separate the quote message and the admin message with BeautifulSoup
                        soup = BeautifulSoup(post['content'], 'html.parser')
                        desc_quote = soup.find('blockquote')
                        if desc_quote is not None:
                            desc_quote = soup.find('blockquote').get_text()
                            for tag in soup.find_all('blockquote'):
                                tag.replaceWith('')
                                desc_admin = soup.find('div', attrs={"class", "ipsType_break ipsType_richText ipsContained"}).get_text()
                        else:
                            desc_admin = soup.find('div', attrs={"class", "ipsType_break ipsType_richText ipsContained"}).get_text()

                        # Remove HTMl and non-ASCII symbols
                        desc_admin = await self.rem_color_code(desc_admin)
                        desc_admin = (''.join([i if ord(i) < 128 else '' for i in desc_admin]))
                        desc_admin = re.sub("\s\s+" , " ", desc_admin)

                        # combine final description (only admin rn)
                        desc = desc_admin
                    
                        # Check if message is too long > add "Read more..." with link if too long
                        if len(desc) >= 1000:
                            desc = desc[:1000]

                        desc += '\n [Read more...]({})'.format(post['postlink'])

                        e = discord.Embed(
                            title=post['threadname'], 
                            description=desc,
                            url=post['threadlink'],
                            color=0xFF0000,
                            timestamp=datetime.strptime(post['pubdate'], "%Y-%m-%dT%H:%M:%SZ"
                        ))
                        e.set_author(
                            name=post['author']['name'],
                            url=post['author']['profilelink'],
                            icon_url=post['author']['imagelink'].replace('//forums-cdn', 'https://forums-cdn')
                        )

                        try:
                            await channel.send(embed=e)
                        except discord.Forbidden:
                            Message(3, "[NEWSFEED][{0}] No permissions in {1}".format(guild, channel))
                            continue
                        except discord.HTTPException as e:
                            Message(3, "[NEWSFEED][{0}] HTTPError: {1}".format(guild, str(e)))
                            continue
                        else:
                            await asyncio.sleep(1)
                            self.c.execute('UPDATE apb_news_feed SET PostID = ? WHERE ID = ?', (post['id'], server[0]))
                            self.connection.commit()
            Message(1, '[NEWSFEED] LOOP COMPLETED (90 s)')
            await asyncio.sleep(90)

    async def item_search(self, query):
        query_converted = query.replace(' ', '%20')
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL + 'search/?q={}'.format(query_converted)) as resp:
                if resp.status == 200:
                    item = await resp.json()
                    return True, item[0]
                else:
                    return False, 'spacer'

    async def weapon_search(self, query):
        query_converted = query.replace(' ', '%20')
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL + 'search/?cat=Weapon&q={}'.format(query_converted)) as resp:
                if resp.status == 200:
                    item = await resp.json()
                    return True, item[0]
                else:
                    return False, 'spacer'

    async def drive_type(self, drivetype):
        if drivetype is 0:
            return 'RWD'
        elif drivetype is 1:
            return 'FWD'
        elif drivetype is 2:
            return 'AWD'
        return 'Unkown'
    
    async def apb_e(self, ctx, title, description=None):
        post = discord.Embed(title=title, description=description, color=0xFF0000)
        post.set_author(name='APB Extension')
        await ctx.send(embed=post)

    async def rem_color_code(self, str):
        TAG_RE = re.compile(r'<[^>]+>')
        return TAG_RE.sub('', str)

    @commands.command(name='pop')
    async def pop(self, ctx):
        try:
            if ctx.message.guild.id == 167252659428917248 and ctx.message.channel.id != 262662844477079563:
                return
        except:
            pass

        await ctx.trigger_typing()
        servers = await utils.api_request(self.API_URL + 'population')

        total_pop = 0
        for server in servers:
            total_pop += (int(server['criminals']) + int(server['enforcers']))

        e = discord.Embed(
            title="APB Population ({0})".format(total_pop), 
            color=0xFF0000,
            timestamp=datetime.strptime(server['time'], '%Y-%m-%dT%H:%M:%SZ'),
            url='https://db.apbvault.net/pop/'
        )

        for server in servers:
            total = int(server['criminals']) + int(server['enforcers'])
            e.add_field(name=server['world'], value="Total: {0}\nCriminals: {1}\nEnforcers: {2}".format(
                total, server['criminals'], server['enforcers']
            ))

        e.set_footer(text='Last update')
        await ctx.send(embed=e)

def setup(bot):
    bot.add_cog(APBDB2(bot))
