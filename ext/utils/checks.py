import settings
from discord.ext import commands


def is_owner():
    def predicate(ctx):
        return ctx.message.author.id == settings.OWNER_ID
    return commands.check(predicate)


def is_owner_server():
    def predicate(ctx):
        if ctx.message.author.id == ctx.message.server.owner.id:
            return ctx.message.author.id == ctx.message.server.owner.id
        else:
            return ctx.message.author.id == settings.OWNER_ID
    return commands.check(predicate)


def can_manage():
    def predicate(ctx):
        try:
            return ctx.message.channel.permissions_for(ctx.message.author).manage_messages
        except:
            return False
    return commands.check(predicate)
