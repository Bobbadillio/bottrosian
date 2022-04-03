import os
import logging
import berserk
import asyncio
import cairosvg
import chess
import chess.svg
import io
from PostgresManager import Postgres

from chessdotcom.aio import get_player_profile, get_player_stats, Client
from chessdotcom.types import ChessDotComError

import discord
from discord.ext import tasks, commands

bot = commands.Bot(command_prefix="!")
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.environ['DATABASE_URL']
POSTGRES_OBJECT = Postgres(DATABASE_URL)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}({bot.user.id})")

ORIGINAL_COMMANDS = """
.lichess
.lichess [lichess username] / .chess [chess.com username] to link your accounts
.update
To update your profile
.unlink
To unlink your chess.com/lichess.org accounts
.profile
To view your profile. To check others profile -> .profile @user
.rank
Displays your current rank in the server (based on your lichess/chess.com rating).
.page
Displays players close to your rank
.top
Displays top 10 players of the server. i.e Leaderboard
.pgn
Pops an image out of PGN. Will be handy for coaches.  Example: .pgn d4 c6 Nf3
verfication (Automatic)
Challenge a person and paste the invite link in any channel :D (lichess only)
.progress
To check your progress"""

# @bot.command()
# async def embed(ctx):
#     embed=discord.Embed(
#     title="Text Formatting",
#         url="https://realdrewdata.medium.com/",
#         description="Here are some ways to format text",
#         color=discord.Color.darker_grey())
#     embed.set_author(name="RealDrewData", url="https://twitter.com/RealDrewData", icon_url="https://cdn-images-1.medium.com/fit/c/32/32/1*QVYjh50XJuOLQBeH_RZoGw.jpeg")
#     #embed.set_author(name=ctx.author.display_name, url="https://twitter.com/RealDrewData", icon_url=ctx.author.avatar_url)
#     embed.set_thumbnail(url="https://i.imgur.com/axLm3p6.jpeg")
#     embed.add_field(name="*Italics*", value="Surround your text in asterisks (\*)", inline=False)
#     embed.add_field(name="**Bold**", value="Surround your text in double asterisks (\*\*)", inline=False)
#     embed.add_field(name="__Underline__", value="Surround your text in double underscores (\_\_)", inline=False)
#     embed.add_field(name="~~Strikethrough~~", value="Surround your text in double tildes (\~\~)", inline=False)
#     embed.add_field(name="`Code Chunks`", value="Surround your text in backticks (\`)", inline=False)
#     embed.add_field(name="Blockquotes", value="> Start your text with a greater than symbol (\>)", inline=False)
#     embed.add_field(name="Secrets", value="||Surround your text with double pipes (\|\|)||", inline=False)
#     embed.set_footer(text="Learn more here: realdrewdata.medium.com")
#
#     await ctx.send(embed=embed)

@bot.command()
async def ping(ctx, *args):
    await ctx.send(f"pong from {ctx.author} with args {','.join(args)}")

@bot.command()
async def chess(ctx, *args):
    """ Should connect once daily to chess.com to:
    get rating change
    update belts
    """
    if len(args)==0:
        await ctx.send(f"thanks {ctx.author}, but your message {ctx.message} had 0 arguments and is invalid")
    else:
        username = args[0]
        try:
            profile = await get_player_profile(username)
        except ChessDotComError:
            await ctx.send(f"Unable to read chess.com profile for {username}")
            return
        try:
            location = profile.player.location
        except AttributeError:
            await ctx.send(f"{username} does not have a location set")
            return
        author = str(ctx.author)
        pg = Postgres(DATABASE_URL)
        user_lookup = pg.query("SELECT * FROM authenticated_users WHERE discord_id = %s",
                               (str(ctx.author)))
        if user_lookup is None:
            if location != author:
                await ctx.send(f"Handshake failed. Your chess.com profile must have its location set to your Discord ID ({author}).")
                return
            else:
                pg.query("""INSERT INTO authenticated_users (discord_id, dojo_belt, mod_awarded_belt)
                VALUES (%s, %s, %s);
                """, (ctx.author, "",""))
        logging.info(user_lookup)
        stats = await get_player_stats(username)
        try:
            rapid_stats = stats.stats.chess_rapid
        except AttributeError:
            await ctx.send(f"{username} does not have a rapid rating")
            return
        rapid_rating = rapid_stats.last.rating
        await ctx.send(f"Your rapid rating on chess.com is {rapid_rating}.\nThat makes you a {chess_com_to_belt(rapid_rating)} Belt.")


@bot.command()
async def lichess(ctx, *args):
    if len(args)==0:
        await ctx.send(f"thanks {ctx.author}, but your message {ctx.message} had 0 arguments and is invalid")
    else:
        username = args[0]
        try:
            client = berserk.Client()
            profile = client.users.get_public_data(username)
            perfs = profile.get("perfs",dict())
            formatted = "\n\t".join([f"{key}:\t{perfs[key].get('rating',0)}" for key in perfs.keys()])
            await ctx.send(f"request to link {username} found profile with ratings:\n\t{formatted}")
        except berserk.exceptions.ResponseError as e:
            await ctx.send(f"request to link {username} failed with error {e}")
        except Exception as e:
            await ctx.send(f"request to link {username} failed with unexpected error {e}")

@bot.command()
async def update(ctx):
    #TODO: requires database interaction
    await ctx.send("update isn't yet implemented")

@bot.command()
async def unlink(ctx):
    #TODO: requires database interaction
    await ctx.send("unlink isn't yet implemented")

@bot.command()
async def profile(ctx):
    #TODO: requires database interaction
    await ctx.send("profile isn't yet implemented")

@bot.command()
async def rank(ctx):
    #TODO: requires database interaction
    await ctx.send("rank isn't yet implemented")

@bot.command()
async def page(ctx):
    #TODO: requires database interaction
    await ctx.send("page isn't yet implemented")

@bot.command()
async def top(ctx):
    #TODO: requires database interaction
    await ctx.send("top isn't yet implemented")

@bot.command()
async def tactic(ctx):
    #TODO: low priority, probably won't implement
    await ctx.send("tactic isn't yet implemented")

@bot.command()
async def open(ctx):
    #TODO: low priority, probably won't implement
    await ctx.send("open isn't yet implemented")

@bot.command()
async def pgn(ctx):

    await ctx.send("pgn isn't yet implemented")

@bot.command()
async def fen(ctx, *, arg):
    board = chess.Board(arg)
    svg = chess.svg.board(board=board)
    png = cairosvg.svg2png(bytestring=svg)
    f = discord.File(io.BytesIO(png), "board.png")
    await ctx.send(file=f)

@bot.command()
async def verification(ctx):
    #TODO: I'm not sure what this should do. Likely won't implement.
    await ctx.send("verification isn't yet implemented")

@bot.command()
async def progress(ctx):
    #TODO: requires database interaction
    await ctx.send("progress isn't yet implemented")

@bot.command()
async def addchess(ctx):
    #TODO: probably overlaps with chess command, probably won't implement
    await ctx.send("addchess isn't yet implemented")

@bot.command()
async def addlichess(ctx):
    #TODO: probably overlaps with lichess command, probably won't implement
    await ctx.send("addlichess isn't yet implemented")

CHESS_COM_BELTS = [
    (2400, "Black"),
    (2200, "Red"),
    (2000, "Brown"),
    (1800, "Purple"),
    (1600, "Blue"),
    (1400, "Green"),
    (1200, "Orange"),
    (1000, "Yellow"),
    (0,    "White")
]

def chess_com_to_belt(rating):
    for (threshold, name) in CHESS_COM_BELTS:
        if rating > threshold:
            return name
    return "No"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot.run(TOKEN)
