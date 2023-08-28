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
from discord.utils import get

bot = commands.Bot(command_prefix="!")
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.environ['DATABASE_URL']
POSTGRES_OBJECT = Postgres(DATABASE_URL)
SUPER_ROLES = ["Sensei", "admin", "Admin", "Mod"]
BELT_COLORS = ["Black", "Red", "Brown", "Purple", "Blue", "Green", "Orange", "Yellow", "White"]

CHESS_COM_BELTS = [
    (2400, "Black"),
    (2100, "Red"),
    (1800, "Purple"),
    (1600, "Blue"),
    (1400, "Green"),
    (1200, "Orange"),
    (1000, "Yellow"),
    (0,    "White")
]

# LICHESS_BELTS = [
#     (2400, "Black"),
#     (2250, "Red"),
#     (2100, "Brown"),
#     (2000, "Purple"),
#     (1800, "Blue"),
#     (1600, "Green"),
#     (1400, "Orange"),
#     (1200, "Yellow"),
#     (0,    "White")
# ]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}({bot.user.id})")


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
    """ link a chess.com account with discord user ID in location. usage: !chess ChesscomUsername"""
    author = str(ctx.author)
    if len(args)==0:
        await ctx.send(f"please specify chess.com username with your discord user ID({author}) in the location field. usage: !chess ChesscomUsername")
        return

    username = args[0]

    # Create the discord user if it doesn't exist
    EnsureDiscordAuthorExists(author)

    # getting chess.com info
    try:
        profile = await get_player_profile(username)
    except ChessDotComError:
        await ctx.send(f"Unable to read chess.com profile for {username}")
        return


    pg = Postgres(DATABASE_URL)
    retrieved_chess_profiles = pg.query("SELECT * from chesscom_profiles WHERE discord_id = %s", (author,))

    if len(retrieved_chess_profiles)==0:
        # first time handshake
        try:
            location = profile.player.location
        except AttributeError:
            await ctx.send(f"{username} does not have a location set. Your chess.com profile must have its location set\
to your Discord ID ({author}). You can change the location back after your profile is linked.")
            return

        if location != author:
            await ctx.send(f"Verification failed. Your chess.com profile must have its location set to your Discord ID\
({author}). You can change the location back after your profile is linked.")
            return

    await update_chesscom(ctx, author, username, quiet=False)
    await update_belt(ctx, author)



@bot.command()
async def lichess(ctx, *args):
    await ctx.send("Bottrosian doesn't currently track lichess accounts.")

@bot.command()
async def update(ctx):
    """Updates your chess.com ratings, and recalculates your belt. usage: !update"""
    pg = Postgres(DATABASE_URL)
    author = str(ctx.author)

    profile_result = pg.query("""SELECT GREATEST(awarded_belt, chesscom_belt) AS belt, 
    chesscom_username, last_chesscom_elo AS chesscom_elo FROM authenticated_users 
    NATURAL LEFT JOIN chesscom_profiles 
    NATURAL LEFT JOIN mod_profiles 
    WHERE discord_id = %s""", (author,))
    old_belt = profile_result[0][0]

    #update chesscom
    retrieved_chesscom_profiles = pg.query("SELECT chesscom_username, chesscom_belt AS old_belt from chesscom_profiles WHERE discord_id = %s", (author,))
    if len(retrieved_chesscom_profiles)>0:
        # perform handshake and perform first time insert
        username = retrieved_chesscom_profiles[0][0]
        await update_chesscom(ctx, author, username, old_belt)

    #update belt
    await update_belt(ctx, author)
    profile_result = pg.query("""SELECT GREATEST(awarded_belt, chesscom_belt) AS belt, 
    chesscom_username, last_chesscom_elo AS chesscom_elo FROM authenticated_users 
    NATURAL LEFT JOIN chesscom_profiles 
    NATURAL LEFT JOIN mod_profiles 
    WHERE discord_id = %s""", (author,))
    new_belt = profile_result[0][0]
    string_to_send = f"Update complete for {author}."
    if old_belt!=new_belt:
        string_to_send += f" {author} has been awarded a {new_belt} belt!"
    await ctx.send(string_to_send)

@bot.command()
async def unlink(ctx, *args):
    """ this command unlinks chess.com, lichess or both profiles with !unlink !unlink chess or !unlink lichess"""
    pg = Postgres(DATABASE_URL)
    author = str(ctx.author)
    if len(args)== 0:
        lichess_deletion = pg.query("""DELETE FROM lichess_profiles WHERE discord_id = %s RETURNING *""", (author,))
        chesscom_deletion = pg.query("""DELETE FROM chesscom_profiles WHERE discord_id = %s RETURNING *""", (author,))
        await ctx.send(f"""Unlinking {ctx.author} from chess.com and lichess. 
        Chess.com {"not " if chesscom_deletion==0 else ""}unlinked. 
        lichess {"not " if lichess_deletion == 0 else ""}unlinked.""")
    else:
        if args[0] == "lichess":
                lichess_deletion = pg.query("""DELETE FROM lichess_profiles WHERE discord_id = %s RETURNING *""", (author,))
                await ctx.send(f"""User {ctx.author} {"not " if lichess_deletion == 0 else ""}unlinked from lichess""")
        elif args[0] == "chess":
                chesscom_deletion = pg.query("""DELETE FROM chesscom_profiles WHERE discord_id = %s RETURNING *""", (author,))
                await ctx.send(f"""User {ctx.author} {"not " if chesscom_deletion == 0 else ""}unlinked from chess.com""")
        else:
            await ctx.send(f"""thanks {ctx.author}, but your message tried to unlink you from '{args[0]}'
            which is invalid. please try !unlink !unlink chess or !unlink lichess""")

@bot.command()
async def profile(ctx, *args):
    """this command returns a profile based on your linked chess.com and/or lichess profiles. usage: !profile"""
    #TODO: Make this look pretty like it used to look!
    profile_headers= ["Discord ID", "Belt", "Chess.com Username", "Chess.com Rapid", "Lichess Username", "Lichess Classical"]
    pg = Postgres(DATABASE_URL)
    discord_id_lookup = str(ctx.author)
    if len(args)>0:
        discord_id_lookup = args[0]


    profile_result = pg.query("""SELECT discord_id AS discord, GREATEST(awarded_belt, chesscom_belt) AS belt, 
    chesscom_username, last_chesscom_elo AS chesscom_elo FROM authenticated_users 
    NATURAL LEFT JOIN chesscom_profiles 
    NATURAL LEFT JOIN mod_profiles 
    WHERE discord_id = %s""", (discord_id_lookup,))

    if len(profile_result)==0:
        await ctx.send(f"discord user {discord_id_lookup} doesn't appear to be linked to an account. Please try the !chess command.")
        return

    message_to_send = []
    discord_id, belt, chesscom_username, chesscom_rapid = profile_result[0]
    message_to_send.append(f"Discord ID: {discord_id}")
    message_to_send.append(f"Belt: {belt}")
    if chesscom_username is not None:
        rating = "provisional" if chesscom_rapid is None else chesscom_rapid
        message_to_send.append(f"Chess.com Rapid: {rating}")

    final_message = '\n'.join(message_to_send)
    await ctx.send(f"{final_message} ")



@bot.command()
async def top(ctx):
    """this command returns a list of the top 10 rated players in the dojo based on chess.com rapid. usage: !top"""
    pg = Postgres(DATABASE_URL)
    chesscom_top_headers = ["chess.com username", "chess.com rapid"]
    chesscom_results = pg.query("""select chesscom_username as username, last_chesscom_elo as elo from chesscom_profiles where last_chesscom_elo IS NOT NULL order by elo desc limit 10;""")
    await ctx.send(f"```{tabulate.tabulate(chesscom_results, headers=chesscom_top_headers)}```\n ")

@bot.command()
async def pgn(ctx, *args):
    """displays a position based on a pgn. usage: !pgn 1.d4 e6 2.e4 d5 3.Nc3 c5 4.Nf3 Nc6 5.exd5 exd5 6.Be2 Nf6 7.O-O"""
    final_position = chesspgn.read_game(io.StringIO(" ".join(args))).end().board()
    svg = chesssvg.board(board=final_position)
    png = cairosvg.svg2png(bytestring=svg)
    f = discord.File(io.BytesIO(png), "board.png")
    await ctx.send(file=f)

@bot.command()
async def fen(ctx, *, arg):
    """displays a position based on a fen. usage: !fen 5rk1/pp4pp/4p3/2R3Q1/3n4/6qr/P1P2PPP/5RK1 w - - 2 24"""
    board = chess_py.Board(arg)
    svg = chess_py.svg.board(board=board)
    png = cairosvg.svg2png(bytestring=svg)
    f = discord.File(io.BytesIO(png), "board.png")
    await ctx.send(file=f)

@bot.command()
async def progress(ctx):
    """not currently implemented. """
    #TODO: requires database interaction
    await ctx.send("progress isn't yet implemented")

@bot.command()
async def delete(ctx, discord_id):
    """Admin/Mod/Sensei role command to delete users from the database."""
    if not is_super_user(ctx.author):
        await ctx.send(f"user {str(ctx.author)} not authorized to delete")
        return
    pg = Postgres(DATABASE_URL)
    pg.query("""DELETE FROM authenticated_users WHERE discord_id = %s RETURNING *""", (discord_id,))
    await ctx.send(f"user {discord_id} deleted by {str(ctx.author)}")

@bot.command()
async def award_belt(ctx, discord_id, color):
    """Admin/Mod/Sensei role command to award users a belt. usage: !award Yellow"""
    if not is_super_user(ctx.author):
        await ctx.send(f"User {str(ctx.author)} not authorized to award belts.")
        return

    pg = Postgres(DATABASE_URL)
    try:
        pg.query("""INSERT INTO mod_profiles VALUES (%s, %s) ON CONFLICT (discord_id) 
            DO UPDATE SET awarded_belt=EXCLUDED.awarded_belt; """, (discord_id, color.strip().capitalize()))
        await ctx.send(f"""{discord_id} was awarded the {color.lower()} belt!""")
    except Exception as error:
        logging.log(logging.WARNING, 'query error: {}'.format(error))
        await ctx.send(f"""An error occurred awarding a belt. Are you sure the belt is a supported color, and the recipient was\
given as a discord ID like username#1234 """)


@bot.command()
async def source(ctx):
    """A command to get a link to this bot's source code on github"""
    await ctx.send(f"""https://github.com/Bobbadillio/bottrosian""")


def is_super_user(author):
    return any([each_role.name in SUPER_ROLES for each_role in author.roles])

async def update_lichess(ctx, profile, old_belt=None, quiet = True):
    await ctx.send(f"Lichess data is no longer tracked by Bottrosian")

async def update_chesscom(ctx, author, username, old_belt=None, quiet = True):
    pg = Postgres(DATABASE_URL)
    live_categories = ['chess_rapid', 'chess_bullet', 'chess_blitz']
    stats = await get_player_stats(username)
    ratings = stats.json.get("stats").keys()
    if not any([rating in live_categories for rating in ratings]):
        await ctx.send(f"{username} does not have a stable bullet/blitz/rapid rating on chess.com. Have you played enough recent games for a stable rating?")
        return

    rapid_rating = stats.json.get("stats", dict()).get("chess_rapid",dict()).get("last",dict()).get("rating")
    mapped_belt = chess_com_to_belt(rapid_rating)
    pg.query("""INSERT INTO chesscom_profiles (chesscom_username, discord_id, last_chesscom_elo, previous_chesscom_elo, chesscom_belt)
        VALUES (%s, %s, %s, %s, %s) ON CONFLICT (chesscom_username) DO UPDATE SET 
        last_chesscom_elo = EXCLUDED.last_chesscom_elo, chesscom_belt = EXCLUDED.chesscom_belt;
        """, (username, author, rapid_rating, rapid_rating, mapped_belt))
    if not quiet:
        await ctx.send(f"Chess.com user successfully linked! Based on Chess.com rapid, {username} has been awarded a {mapped_belt.lower()} belt")

async def setbelt(ctx, color):
    member = ctx.message.author

    retrieved = get(member.guild.roles, name=f"{color} Belt")
    if retrieved is None:
        await ctx.send(f"No such role {color} Belt. Please pick one of: {' '.join(BELT_COLORS)}")
        return

    # old_belts = [each_role for each_role in member.roles if "Belt" in each_role.name and each_role.name!=f"{color} Belt"]
    # if len(old_belts)>0:
    #     await member.remove_roles(*old_belts)
    await member.add_roles(retrieved)

async def update_belt(ctx, discord_id):
    pg = Postgres(DATABASE_URL)
    highest_belt = pg.query("""SELECT GREATEST(awarded_belt, chesscom_belt) AS belt FROM authenticated_users 
        NATURAL LEFT JOIN mod_profiles 
        NATURAL LEFT JOIN chesscom_profiles
         WHERE discord_id = %s;""", (discord_id, ))
    await setbelt(ctx, highest_belt[0][0])

def chess_com_to_belt(rating):
    if rating is None:
        return "White"
    for (threshold, name) in CHESS_COM_BELTS:
        if rating > threshold:
            return name
    return "White"

def EnsureDiscordAuthorExists(author):
    """Adds authenticated users if doesn't exist"""
    pg = Postgres(DATABASE_URL)
    pg.query("""INSERT INTO authenticated_users VALUES (%s) ON CONFLICT DO NOTHING; """, (author,))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot.run(TOKEN)
