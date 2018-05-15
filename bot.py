import discord
import logging
import ext.ams

from settings import *
from ext.utils import utils
from discord.ext import commands


EXTS = [
    'admin',
    'ams',
    'bg_tasks',
    'general',
    'gfycat',
    'help',
    'imgur',
    'lfg',
    'moderation',
    'pubg',
    'apbdb2',
    'twitch'
]

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(PREFIX),            
    description=DESCRIPTION,
    pm_help=None,
    help_attrs=dict(hidden=True)
)


@bot.event
async def on_ready():
    print('[discord]Bot {0.name} : {0.id}'.format(bot.user))
    print('[discord]Library: Discord.py {}'.format(discord.__version__))

    print('[exts]Loading {0} extensions. Please wait...'.format(len(EXTS)))
    for ext in EXTS:
        try:
            bot.load_extension('ext.' + ext)
            print('[exts]Extension "{0}" loaded.'.format(ext))
        except ImportError as e:
            pass
        except Exception as e:
            print('[extension]Failed to initialize extension "{}". Error: {}'.format(ext, e))
    print('[exts]Loading complete.')

@bot.event
async def on_message(message):
    await AMS.message_check(message)
    if message.author.id is bot.user.id:
        return
    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
    print('[discord]Bot joined guild {0.name} : {0.id}'.format(guild))
    Utils.add_guild(guild)

@bot.event
async def on_guild_remove(guild):
    print('[discord]Bot left guild {0.name} : {0.id}'.format(guild))
    Utils.del_guild(guild)


if __name__ == '__main__':
    Utils = utils.Setup(bot)
    AMS = ext.ams.AMS(bot)
    bot.run(TOKEN)

