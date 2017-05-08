import discord

from settings import *
from ext.utils import utils
from discord.ext import commands


initial_extensions = [
    'admin',
    'general',
    'moderation'
]

bot = commands.Bot(command_prefix=commands.when_mentioned_or(PREFIX),
                   description=DESCRIPTION,
                   pm_help=None,
                   help_attrs=dict(hidden=True))


@bot.event
async def on_ready():
    print('[discord]Bot {0.name} : {0.id}'.format(bot.user))
    print('[discord]Library: Discord.py {}'.format(discord.__version__))

    for extension in initial_extensions:
        try:
            bot.load_extension('ext.' + extension)
        except Exception as e:
            print('[extension]Failed to initialize extension "{}". Error: {}'.format(extension, e))


@bot.event
async def on_message(message):
    print('[message]{0.server.id} : {0.author} : {0.content}'.format(message))
    await bot.process_commands(message)


@bot.event
async def on_server_join(server):
    print('[discord]Bot joined server {0.name} : {0.id}'.format(server))
    inst_utils.add_server(server)


@bot.event
async def on_server_remove(server):
    print('[discord]Bot left server {0.name} : {0.id}'.format(server))
    inst_utils.del_server(server)

if __name__ == '__main__':
    inst_utils = utils.Setup(bot)
    bot.run(TOKEN)
