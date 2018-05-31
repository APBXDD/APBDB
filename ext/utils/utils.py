import aiohttp
import async_timeout
import sqlite3
import websockets
import json

from settings import *
from datetime import datetime
from colorama import init, Fore, Back, Style
init(autoreset=True)


async def api_request(url):
    """makes an api request and returns it in json, return status if request failed"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return resp.status

async def service_call(self, *args, **kwargs):
    async with websockets.connect('ws://localhost:9200/beacon') as websocket:
        payload = json.dumps( {"method":methodName, "args":args, "kwargs": kwargs})
        await websocket.send(payload)
        #...
        resp = await websocket.recv()
        #...
        return resp

async def bot_init(bot):
    """ Gets game, username and avatar and updates the bot

        NOT WORKING RIGHT NOW!
    """
    try:
        connection = sqlite3.connect(DATABASE)
        connection.execute('SELECT * FROM bot')
        sett = connection.fetchone()

        await bot.edit_profile(username=sett[4])
        await bot.change_status(game=sett[1])

        if sett[5] is not None:
            with aiohttp.ClientSession() as session:
                async with session.get(sett[5]) as resp:
                    await bot.edit_profile(avatar=await resp.read())
    except Exception as e:
        print('[init]Error: {}'.format(e))


class Setup:
    def __init__(self, bot):
        self.bot = bot

        self.connection = sqlite3.connect(DATABASE)
        self.c = self.connection.cursor()

        self.check_tables()
        #self.bot_init()

    def __del__(self):
        self.c.close()
        self.connection.close()

    def check_tables(self):
        print('[database]Checking tables...')
        try:
            f = open('.setup/spdb.sql', 'r')
            sql = f.read()
            sql_queries = sql.split(';')

            for query in sql_queries:
                self.c.execute(query)
        except Exception as e:
            print('[database]Error in setup: {}\nExiting...'.format(e))
            exit()
        else:
            print('[database]Performing database clean-up...')
            self.c.execute("VACUUM")
            self.connection.commit()
            print('[database]Tables checked and up-to-date!')

    def add_guild(self, guild):
        try:
            self.c.execute('INSERT INTO servers VALUES (?, ?, 0, 0, 1)', (guild.id, guild.name))
        except Exception as e:
            print('[database]Error in add_guild: {}'.format(e))
            guild.leave()
        finally:
            self.connection.commit()
            print('[database]Guild {0.name} : {0.id} added!'.format(guild))

    def del_guild(self, guild):
        try:
            self.c.execute('DELETE FROM servers WHERE ID = ?', [guild.id])
            self.c.execute('DELETE FROM timeouts WHERE ServerID = ?', [guild.id])
            self.c.execute('DELETE FROM twitch WHERE ServerID = ?', [guild.id])
            self.c.execute('DELETE FROM apb_news_feed WHERE ID = ?', [guild.id])
            self.c.execute('DELETE FROM lfg WHERE ServerID = ?', [guild.id])
        except Exception as e:
            print('[database]Error in del_guild: {}'.format(e))
        finally:
            self.connection.commit()
            print('[database]Guild {0.name} : {0.id} removed!'.format(guild))


class Message:
    """
        Class for console messages

        Types:
         - empty = regular
         - 1 = debug
         - 2 = alert
         - 3 = error
    
    """
    def __init__(self, type: int, message:str):
        self.type = type
        self.message = message
        self.time = "[{0}]".format(datetime.now().strftime("%d-%m %H:%M:%S"))
        self.useDebug = True
        self.selection()
        
    def selection(self):
        final = ""

        try:
            if self.type is 1:
                final = self.debug()
            elif self.type is 2:
                final = self.alert()
            elif self.type is 3:
                final = self.error()
            else:
                final = self.default()
        except Exception as e:
            print(str(e))
        else:
            if self.type is not 1:
                print(final)
            elif self.type is 1 and self.useDebug is True:
                print(final)

    def default(self):
        return "{0} {1}".format(self.time, self.message)

    def debug(self):
        return "{0}{1}{2}[DEBUG] {3}".format(Style.DIM, Fore.WHITE, self.time, self.message)

    def alert(self):
        return "{0}{1}[ALERT] {2}".format(Fore.YELLOW, self.time, self.message)

    def error(self):
        return "{0}{1}[ERROR] {2}".format(Fore.RED, self.time, self.message)
