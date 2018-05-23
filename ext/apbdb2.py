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


class APBDB2:
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE)
        self.c = self.connection.cursor()

        self.news_feed_lock = asyncio.Lock()
        self.news_feed = bot.loop.create_task(self.news_feed())

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

        search = await self.item_search(query)
        if search[0] is True:
            item = await utils.api_request(self.API_URL + 'items/{}'.format(search[1]['sapbdb']))
            e = discord.Embed(title=str(item['item_detail']['sdisplayname']),
                              description=str(item['item_detail']['sdescription']),
                              url=str(item['url']),
                              color=0xFF0000)
            if item['Category'] == 'Modifications':
                for effect in item['ModifierEffects']:
                    value = '**Multiplier:** {}  \n**Add:** {}'.format(str(effect['feffectmultiplier']), str(effect['faddtoresult']))
                    e.add_field(name=await self.rem_color_code(str(effect['sdescription'])), value=value)
            elif item['Category'] == 'Vehicles':
                e.add_field(name='Max Health', value='{} '.format(item['VehicleSetupType']['nmaxhealth']))
                e.add_field(name='Max Speed', value='{} m/s'.format(item['VehicleSetupType']['fmaxspeed']))
                e.add_field(name='Max Reverse Speed', value='{} m/s'.format(item['VehicleSetupType']['fmaxreversespeed']))
                e.add_field(name='Max Explosion Damage', value='{} at {} cm'.format(item['Explosions']['ndamage'], round(item['Explosions']['fgroundzeroradius'], 0)))
                e.add_field(name='Cargo Capacity', value='{}'.format(item['VehicleSetupType']['nmaincargopipcapacity']))
                e.add_field(name='Drive Type', value=await self.drive_type(item['VehicleSetupType']['edrivetype']))
            elif item['Category'] == 'Weapons':
                try:
                    e.add_field(name='TTK / STK', value='{} sec / {}'.format(round(item['calculated']['timetokill_effect'], 2), item['calculated']['shottokill_effect']))
                    e.add_field(name='TTS / STS', value='{} sec / {}'.format(round(item['calculated']['timetostun_effect'], 2), item['calculated']['shottostun_effect']))
                except:
                    e.add_field(name='TTK / STK', value='{} sec / {}'.format(round(item['calculated']['timetokill'], 2), item['calculated']['shottokill']))
                    e.add_field(name='TTS / STS', value='{} sec / {}'.format(round(item['calculated']['timetostun'], 2), item['calculated']['shottostun']))
                
                if detail is True:
                    e.add_field(
                        name='DMG / STM / HRD', 
                        value='{} / {} / {}'.format(
                            item['WeaponType']['fhealthdamage'], 
                            item['WeaponType']['fstaminadamage'], 
                            round((item['WeaponType']['fharddamagemodifier'] * item['WeaponType']['fhealthdamage']), 2)
                        )
                    )
                    e.add_field(
                        name='MAG / POOL',
                        value='{} / {}'.format(
                            item['WeaponType']['nmagazinecapacity'],
                            item['WeaponType']['nammopoolcapacity']
                        ),
                    )
            e.set_thumbnail(url=str(item['icon_url']))
            await ctx.send(embed=e)
        else:
            await ctx.send(embed=discord.Embed(
                title='Error', 
                description='Item not found. Your query: "{}"'.format(query), 
                color=0xFF0000
            ))

    @commands.group(name='apb')
    async def apb(self, ctx):
        if ctx.invoked_subcommand is None:
           pass 

    @apb.group(name='feed', no_pm=True)
    @checks.can_manage()
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
            self.c.execute('UPDATE apb_news_feed SET ChannelID = ? WHERE ID = ?', (ctx.message.channel.id, ctx.message.guild.id))
            self.connection.commit()
            await self.apb_e(ctx, 'News Feed', 'APB news Feed channel updated.')
        except Exception as e:
            await ctx.send(embed=discord.Embed(title='Error', description=str(e), color=0xFF0000))
        else:
            self.connection.commit()
            await self.apb_e(ctx, 'News Feed', 'Channel set.')

    @commands.command(name='role', no_pm=True)
    async def role(self, ctx, role: str):
        roles = ['Citadel', 'Jericho', 'Han', 'Nekrova']
        try:
            if role.lower() == 'citadel':
                role = discord.utils.get(ctx.message.guild.roles, name='Citadel')
                await self.manage_role(ctx, role)
            elif role.lower() == 'jericho':
                role = discord.utils.get(ctx.message.guild.roles, name='Jericho')
                await self.manage_role(ctx, role)
            elif role.lower() == 'nekrova':
                role = discord.utils.get(ctx.message.guild.roles, name='Nekrova')
                await self.manage_role(ctx, role)
            elif role.lower() == 'han':
                role = discord.utils.get(ctx.message.guild.roles, name='Han')
                await self.manage_role(ctx, role)
        except Exception as e:
            await ctx.send('Error: {}'.format(e))

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
                
    async def news_feed(self):
        print('[bg] APB News Feed active')
        while not self.bot.is_closed():
            self.c.execute('SELECT ID, ChannelID, PostID, ShowMods FROM apb_news_feed')
            servers = self.c.fetchall()
            print("[DEBUG][nf] Checking {0} servers...".format(len(servers)))
            
            for server in servers:
                guild = self.bot.get_guild(int(server[0]))
                if guild is None:
                    print("[DEBUG][nf] Could not get guild with ID {}".format(server[0]))
                    continue
                if int(server[1]) is not 0:
                    print("[DEBUG] Getting channel {0} for guild {1}".format(server[1], guild))
                    try:
                        channel = guild.get_channel(int(server[1]))
                    except discord.NotFound:
                        continue
                    print("[DEBUG] Guild {0} using channel {1}".format(guild, channel))
                    if channel is None:
                        print("[DEBUG][nf] Could not get channel for guild {}".format(guild))
                        continue
                else:
                    continue
                print("[DEBUG][nf] [{0}] Channel found: {1}".format(guild, channel))
                postID = server[2]
                mods = server[3]
                if mods is 0:
                    request_url = self.API_URL + 'tracker?mod=False&currentid={}'.format(postID)
                else:
                    request_url = self.API_URL + 'tracker?currentid={}'.format(postID)
                print("[DEBUG][nf] [{0}] Attempting API request: {1}".format(guild, request_url))
                posts = []
                posts = await utils.api_request(request_url)
                try:
                    if posts > 200 and posts < 200:
                        print("[DEBUG][nf] Error: Request did not return JSON - Status: {}".format(posts))
                        continue
                except:
                    pass

                
                print('[DEBUG][nf] [{0}] Processing {1} new posts in {2}.'.format(guild, len(posts), channel))

                if len(posts) > 0 and not isinstance(posts, int):
                    for post in reversed(posts):
                        # separate the quote message and the admin message with BeautifulSoup
                        soup = BeautifulSoup(post['content'], 'html.parser')
                        desc_quote = soup.find('blockquote')
                        if desc_quote is not None:
                            desc_quote = soup.find('blockquote').get_text()
                            for tag in soup.find_all('blockquote'):
                                tag.replaceWith('')
                                desc_admin = soup.find('div').get_text()
                        else:
                            desc_admin = soup.find('div').get_text()

                        # Remove HTMl and non-ASCII symbols
                        desc_admin = await self.rem_color_code(desc_admin)
                        desc_admin = (''.join([i if ord(i) < 128 else '' for i in desc_admin]))

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
                            icon_url=post['author']['imagelink']
                        )

                        try:
                            await channel.send(embed=e)
                        except discord.Forbidden:
                            print("[DEBUG][nf] [{0}] No permissions in {1}".format(guild, channel))
                            continue
                        except discord.HTTPException as e:
                            print("[DEBUG][nf]HTTPError in {0} - {1}".format(guild, str(e)))
                            continue
                        else:
                            await asyncio.sleep(1)
                            self.c.execute('UPDATE apb_news_feed SET PostID = ? WHERE ID = ?', (post['id'], server[0]))
                            self.connection.commit()
            print('[DEBUG] APB NEWS FEED : EVENT : LOOP COMPLETED (90 s)')
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
        await ctx.send(ctx.message.channel, embed=post)

    async def rem_color_code(self, str):
        TAG_RE = re.compile(r'<[^>]+>')
        return TAG_RE.sub('', str)

def setup(bot):
    bot.add_cog(APBDB2(bot))
