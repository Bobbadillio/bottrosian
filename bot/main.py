import os
import logging


from discord.ext import tasks, commands

bot = commands.Bot(command_prefix="!")
TOKEN = os.getenv("DISCORD_TOKEN")

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
.tactic
To solve tactics from chess.com
.open [chess opening name here]/[ECO codes]
To view an opening. Please dont spam with it
.pgn
Pops an image out of PGN. Will be handy for coaches.  Example: .pgn d4 c6 Nf3
verfication (Automatic)
Challenge a person and paste the invite link in any channel :D (lichess only)
.progress
To check your progress
.addchess
Add your chess.com account as an addition to lichess
.addlichess
Add your lichess.org account as an addition to chess"""

@bot.command()
async def ping(ctx, *args):
    await ctx.send(f"pong from {ctx.author} with args {','.join(args)}")

@bot.command()
async def chess(ctx):
    """ Should connect once daily to chess.com to:
    get rating change
    update belts

    """
    await ctx.send("linking to chess.com profiles isn't yet implemented")

@bot.command()
async def lichess(ctx, *args):
    if len(args)==0:
        await ctx.send(f"thanks {ctx.author}, but your message {ctx.message} had 0 arguments and is invalid")
    else:
        username = args[0]
        try:
            client = berserk.Client()
            profile = client.users.get_public_data("festivity")
            await ctx.send(f"request to link {username} found profile with ratings {profile.get('perfs','')}")
        except berserk.exceptions.ResponseError as e:
            await ctx.send(f"request to link {username} failed with error {e}")
        except Exception as e:
            await ctx.send(f"request to link {username} failed with unexpected error {e}")

@bot.command()
async def update(ctx):
    await ctx.send("update isn't yet implemented")

@bot.command()
async def unlink(ctx):
    await ctx.send("unlink isn't yet implemented")

@bot.command()
async def profile(ctx):
    """old content looked like:
    Ratings
1906 (rapid)
Mapped Website
lichess.org
Link
https://lichess.org/@/giziti
Blitz
1878 (682 games)
Bullet
1512 (5003 games)
Rapid
1906 (73 games)
Classical
1822 (73 games)
Other accounts:
None

Ratings of chess.com are adjusted to lichess ratings

    """
    await ctx.send("profile isn't yet implemented")

@bot.command()
async def rank(ctx):
    await ctx.send("rank isn't yet implemented")

@bot.command()
async def page(ctx):
    await ctx.send("page isn't yet implemented")

@bot.command()
async def top(ctx):
    await ctx.send("top isn't yet implemented")

@bot.command()
async def tactic(ctx):
    await ctx.send("tactic isn't yet implemented")

@bot.command()
async def open(ctx):
    await ctx.send("open isn't yet implemented")

@bot.command()
async def pgn(ctx):

    await ctx.send("pgn isn't yet implemented")

@bot.command()
async def fen(ctx):
    """Good first try! No stateful interaction with a database or chess.com/lichess api is required"""
    logging.info("logging test")
    await ctx.send("fen isn't yet implemented")

@bot.command()
async def verification(ctx):
    await ctx.send("verification isn't yet implemented")

@bot.command()
async def progress(ctx):
    await ctx.send("progress isn't yet implemented")

@bot.command()
async def addchess(ctx):
    await ctx.send("addchess isn't yet implemented")

@bot.command()
async def addlichess(ctx):
    await ctx.send("addlichess isn't yet implemented")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot.run(TOKEN)
