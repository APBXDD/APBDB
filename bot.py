import discord
import logging
import ext.ams

from settings import *
from ext.utils import utils
from discord.ext import commands
from ext.utils.utils import Message


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
    Message(2, '[BOT] {0.name} : {0.id}'.format(bot.user))
    Message(2, '[BOT]Library: Discord.py {}'.format(discord.__version__))

    Message(2, '[EXTENSION]Loading {0} extensions. Please wait...'.format(len(EXTS)))
    for ext in EXTS:
        try:
            bot.load_extension('ext.' + ext)
            Message(2, '[EXTENSION] "{0}" loaded.'.format(ext))
        except ImportError as e:
            pass
        except Exception as e:
            Message(3, '[EXTENSION]Failed to initialize extension "{}". Error: {}'.format(ext, e))
    Message(2, '[EXTENSION]Loading complete.')

@bot.event
async def on_message(message):
    if message.author.id is bot.user.id:
        return
    await bot.process_commands(message)
    await AMS.message_check(message)

@bot.event
async def on_guild_join(guild):
    Message(2, '[BOT] Joined guild {0.name} : {0.id}'.format(guild))
    Utils.add_guild(guild)

@bot.event
async def on_guild_remove(guild):
    Message(2, '[BOT] Left guild {0.name} : {0.id}'.format(guild))
    Utils.del_guild(guild)

@bot.event
async def on_guild_unavailable(guild):
    Message(2, '[BOT] Guild {0.name} : {0.id} is unavailable!'.format(guild))

@bot.event
async def on_command_error(ctx, error):
    if type(error).__name__ == 'CommandNotFound':
        return

    Message(3, '[COMMAND] {0.command} : {1}'.format(ctx, error))

    if ctx.guild is not None:
        fmt = '**{0.guild} ({0.guild.id})**\n'\
              '{0.author} ({0.author.id})\n\n'.format(ctx)
    else:
        fmt = '**{0.author} ({0.author.id})**\n\n'.format(ctx)
    
    fmt += 'Error in command "{0.command}"\n'\
           '{1}'.format(ctx, error)
          
    user = bot.get_user(OWNER_ID)
    await user.send(fmt)


if __name__ == '__main__':
    Utils = utils.Setup(bot)
    AMS = ext.ams.AMS(bot)
    bot.run(TOKEN)
