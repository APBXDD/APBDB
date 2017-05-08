import sqlite3

from settings import *


class Setup:
    def __init__(self, bot):
        self.bot = bot

        self.conn = sqlite3.connect(DATABASE)
        self.check_for_tables()

    def check_for_tables(self):
        print('[database]Checking for tables...')
        try:
            c = self.conn.cursor()

            f = open('.setup/spdb.sql', 'r')
            sql = f.read()
            sql_queries = sql.split(';')

            for query in sql_queries:
                c.execute(query)
        except Exception as e:
            print('[database]Error in setup: {}\nExiting...'.format(e))
            exit()
        finally:
            self.conn.commit()
            print('[database]Tables set-up!')

    def add_server(self, server):
        try:
            c = self.conn.cursor()
            c.execute('INSERT INTO servers VALUES ({0.id}, "{0.name}", 0, 0)'.format(server))
            c.execute('INSERT INTO moderators VALUES ({0.owner.id}, {0.id}, 1)'.format(server))
        except Exception as e:
            print('[database]Error in add_server: {}'.format(e))
            self.bot.leave_server(server)
        finally:
            self.conn.commit()
            print('[database]Server {0.name} : {0.id} added!'.format(server))

    def del_server(self, server):
        try:
            c = self.conn.cursor()
            c.execute('DELETE FROM servers WHERE ID = {0.id}'.format(server))
            c.execute('DELETE FROM moderators WHERE ServerID = {0.id}'.format(server))
        except Exception as e:
            print('[database]Error in del_server: {}'.format(e))
        finally:
            self.conn.commit()
            print('[database]Server {0.name} : {0.id} removed!'.format(server))


class Utils:
    def __init__(self, bot):
        self.bot = bot
