import discord


async def default_exception(e):
    embed = discord.Embed(
        title='Error',
        description='{0}\n\nArgs:{0.args}'.format(e)
    )
    return embed

