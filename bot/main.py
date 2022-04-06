import os
import logging
import berserk
import asyncio
import tabulate
import cairosvg
import chess as chess_py
import chess.svg as chesssvg
import chess.pgn as chesspgn
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
async def chess(ctx, *args):
    """ Should connect once daily to chess.com to:
    get rating change
    update belts
    """
    if len(args)==0:
        await ctx.send(f"thanks {ctx.author}, but your message {ctx.message} had 0 arguments and is invalid")
    else:
        username = args[0]
        author = str(ctx.author)

        EnsureAuthorExists(author)

        # getting chess.com info
        try:
            profile = await get_player_profile(username)
        except ChessDotComError:
            await ctx.send(f"Unable to read chess.com profile for {username}")
            return


        pg = Postgres(DATABASE_URL)
        retrieved_chess_profiles = pg.query("SELECT * from chesscom_profiles WHERE discord_id = %s", (author,))
        if len(retrieved_chess_profiles)==0:
            retrieved_chess_profile = None
        else:
            retrieved_chess_profile = retrieved_chess_profiles[0]

        if retrieved_chess_profile is None:
            try:
                location = profile.player.location
            except AttributeError:
                await ctx.send(f"{username} does not have a location set. Your chess.com profile must have its location set to your Discord ID ({author})")
                return

            if location != author:
                await ctx.send(f"Handshake failed. Your chess.com profile must have its location set to your Discord ID ({author}).")
                return
            else:
                stats = await get_player_stats(username)
                try:
                    rapid_stats = stats.stats.chess_rapid
                except AttributeError:
                    await ctx.send(f"{username} does not have a rapid rating. Have you played enough games for a stable rating?")
                    return
                rapid_rating = rapid_stats.last.rating
                mapped_belt = chess_com_to_belt(rapid_rating)
                pg.query("""INSERT INTO chesscom_profiles (chesscom_username, discord_id, last_chesscom_elo, previous_chesscom_elo)
                    VALUES (%s, %s, %s, %s);
                    """, (username, author, rapid_rating, rapid_rating))
                pg.query("""UPDATE authenticated_users SET dojo_belt = GREATEST(dojo_belt, %s)""",(mapped_belt,))
                await ctx.send(
                    f"Your rapid rating on chess.com is {rapid_rating}.\nThat makes you a {mapped_belt} Belt.")
        else:
            await ctx.send(f"Skipping handshake. User {ctx.author} already in database. found {retrieved_chess_profile}.\nTry !update or !profile")




def EnsureAuthorExists(author):
    """Adds authenticated users if doesn't exist"""
    pg = Postgres(DATABASE_URL)
    user_lookups = pg.query("SELECT * FROM authenticated_users WHERE discord_id = %s",
                           (author,))
    if len(user_lookups) == 0:
        user_lookup = None
    else:
        user_lookup = user_lookups[0]

    if user_lookup is None:
        pg.query("""INSERT INTO authenticated_users (discord_id, dojo_belt, mod_awarded_belt)
            VALUES (%s, %s, %s);
            """, (author, None, None))


@bot.command()
async def lichess(ctx, *args):
    if len(args)==0:
        await ctx.send(f"thanks {ctx.author}, but your message {ctx.message} had 0 arguments and is invalid")
    else:
        username = args[0]
        author = str(ctx.author)

        EnsureAuthorExists(author)
        try:
            pg = Postgres(DATABASE_URL)
            retrieved_lichess_profiles = pg.query("SELECT * from lichess_profiles WHERE discord_id = %s", (author,))
            if len(retrieved_lichess_profiles) == 0:
                retrieved_lichess_profile = None
            else:
                retrieved_lichess_profile = retrieved_lichess_profiles[0]

            if retrieved_lichess_profile is not None:
                await ctx.send(f"Skipping handshake. User {ctx.author} already in database. Try !update or !profile")
            else:
                client = berserk.Client()
                profile = client.users.get_public_data(username)
                bio = profile.get("profile", dict()).get("bio", "")
                if author not in bio:
                    await ctx.send(f"Handshake failed. Your lichess profile must have your Discord ID ({author}) in your bio")
                    return
                else:
                    classical =  profile.get("perfs",dict()).get("classical",dict())
                    if classical.get('prov',False) and classical.get("rating") is not None:
                        await ctx.send(f"{username} does not have a classical rating. Have you played enough games on lichess for a stable rating?")
                    else:
                        classical_rating = classical.get("rating")
                        mapped_belt = lichess_to_belt(classical_rating)
                        pg.query("""INSERT INTO lichess_profiles (chesscom_username, discord_id, last_chesscom_elo, previous_chesscom_elo)
                            VALUES (%s, %s, %s, %s);
                            """, (username, author, classical_rating, classical_rating))
                        pg.query("""UPDATE authenticated_users SET dojo_belt = GREATEST(dojo_belt, %s)""",(mapped_belt,))
                        await ctx.send(
                            f"Your classical rating on lichess is {classical_rating}.\nThat makes you a {mapped_belt} Belt.")

        except berserk.exceptions.ResponseError as e:
            await ctx.send(f"request to link {username} failed with error {e}")
        except Exception as e:
            await ctx.send(f"request to link {username} failed with unexpected error {e}")

@bot.command()
async def update(ctx):
    #TODO: requires database interaction
    await ctx.send("update isn't yet implemented")

@bot.command()
async def unlink(ctx, *args):
    if len(args)== 0:
        await ctx.send(f"""thanks {ctx.author}, but your message had 0 arguments and is invalid. Please retry 
        with either !unlink chess or !unlink lichess""")
    else:
        pg = Postgres(DATABASE_URL)
        author = str(ctx.author)
        if args[0] == "lichess":
                deletion_result = pg.query("""DELETE FROM lichess_profiles WHERE discord_id = %s RETURNING *""", (author,))
                await ctx.send(f"""User {ctx.author} removed? {deletion_result}""")
        elif args[0] == "chess":
                deletion_result = pg.query("""DELETE FROM chesscom_profiles WHERE discord_id = %s RETURNING *""", (author,))
                await ctx.send(f"""User {ctx.author} removed? {deletion_result}""")
        else:
            await ctx.send(f"""thanks {ctx.author}, but your message {ctx.message} tried to unlink you from '{args[0]}'
            which is invalid. please try !unlink chess or !unlink lichess""")

@bot.command()
async def profile(ctx, *args):
    profile_headers= ["discord id", "belt", "chess.com username", "chess.com rapid", "lichess username", "lichess classical"]
    pg = Postgres(DATABASE_URL)
    if len(args)==0:
        profile_result = pg.query("""select discord_id as discord, dojo_belt as belt, chesscom_username, last_chesscom_elo as chesscom_elo, lichess_username, last_lichess_elo as lichess_elo from authenticated_users natural left join chesscom_profiles natural left join lichess_profiles WHERE discord_id = %s""", (str(ctx.author),))
    else:
        pg = Postgres(DATABASE_URL)
        profile_result = pg.query("""select discord_id as discord, dojo_belt as belt, chesscom_username, last_chesscom_elo as chesscom_elo, lichess_username, last_lichess_elo as lichess_elo from authenticated_users natural left join chesscom_profiles natural left join lichess_profiles WHERE discord_id = %s""", (args[0],))

    message_to_send = []
    for header, value in zip(profile_headers, profile_result):
        message_to_send.append(f"{header}: {value}")
    final_message = '\n'.join(message_to_send)
    await ctx.send(f"{final_message} ")

# @bot.command()
# async def rank(ctx):
#     #TODO: requires database interaction
#     await ctx.send("rank isn't yet implemented")

# @bot.command()
# async def page(ctx):
#     #TODO: requires database interaction
#     await ctx.send("page isn't yet implemented")

@bot.command()
async def top(ctx):
    pg = Postgres(DATABASE_URL)
    chesscom_top_headers = ["chess.com username", "chess.com rapid"]
    chesscom_results = pg.query("""select chesscom_username as username, last_chesscom_elo as elo from chesscom_profiles order by elo desc limit 10;""")
    await ctx.send(f"```{tabulate.tabulate(chesscom_results, headers=chesscom_top_headers)}```\n ")

    lichess_top_headers = ["lichess username", "lichess classical"]
    lichess_results = pg.query(
        """select lichess_username as username, last_lichess_elo as elo from lichess_profiles order by elo desc limit 10;""")
    await ctx.send(f"```{tabulate.tabulate(lichess_results,headers=lichess_top_headers)}```\n ")

# @bot.command()
# async def tactic(ctx):
#     #TODO: low priority, probably won't implement
#     await ctx.send("tactic isn't yet implemented")

# @bot.command()
# async def open(ctx):
#     #TODO: low priority, probably won't implement
#     await ctx.send("open isn't yet implemented")

@bot.command()
async def pgn(ctx, *args):
    final_position = chesspgn.read_game(io.StringIO(" ".join(args))).end().board()
    svg = chesssvg.board(board=final_position)
    png = cairosvg.svg2png(bytestring=svg)
    f = discord.File(io.BytesIO(png), "board.png")
    await ctx.send(file=f)

@bot.command()
async def fen(ctx, *, arg):
    board = chess_py.Board(arg)
    svg = chess_py.svg.board(board=board)
    png = cairosvg.svg2png(bytestring=svg)
    f = discord.File(io.BytesIO(png), "board.png")
    await ctx.send(file=f)

# @bot.command()
# async def verification(ctx):
#     #TODO: I'm not sure what this should do. Likely won't implement.
#     await ctx.send("verification isn't yet implemented")

@bot.command()
async def progress(ctx):
    #TODO: requires database interaction
    await ctx.send("progress isn't yet implemented")

# @bot.command()
# async def addchess(ctx):
#     #TODO: probably overlaps with chess command, probably won't implement
#     await ctx.send("addchess isn't yet implemented")

# @bot.command()
# async def addlichess(ctx):
#     #TODO: probably overlaps with lichess command, probably won't implement
#     await ctx.send("addlichess isn't yet implemented")

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

LICHESS_BELTS = [
    (2400, "Black"),
    (2200, "Red"),
    (2100, "Brown"),
    (2000, "Purple"),
    (1800, "Blue"),
    (1600, "Green"),
    (1400, "Orange"),
    (1200, "Yellow"),
    (0,    "White")
]

def chess_com_to_belt(rating):
    for (threshold, name) in CHESS_COM_BELTS:
        if rating > threshold:
            return name
    return "No"

def lichess_to_belt(rating):
    for (threshold, name) in LICHESS_BELTS:
        if rating > threshold:
            return name
    return "No"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot.run(TOKEN)
