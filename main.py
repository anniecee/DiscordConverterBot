#Discord points conversion bot
#Python

#Import libraries:
import os
import discord
import sqlite3
from discord.ext import commands
from fractions import Fraction
from keep_alive import keep_alive

#Connect database
conn = sqlite3.connect('pointsdb.sqlite3')
cur = conn.cursor()

#Enable Intents
intents = discord.Intents(messages=True, guilds=True)
intents.presences = True

#Create a new bot object with a specified prefix
bot = commands.Bot(command_prefix="$", intents=intents)

#Remove the default $help command to override it
bot.remove_command('help')

#Function to convert from lowercases to uppercases
def to_upper(arg):
  return arg.upper()

#Print to screen when bot is ready
@bot.event
async def on_ready():
  print('Bot is ready.')

#Send first message when bot joins a new channel
@bot.event
async def on_guild_join(guild):
  for channel in guild.text_channels:
    if channel.permissions_for(guild.me).send_messages:
      #Command list to display in message
      command_list = '''\
      \U0001F539 `$all`
      List all supported point programs.

      \U0001F539 `$list <program_symbol>`
      List all point programs that are convertible from your chosen point program.
      Example: `$list HSBC`

      \U0001F539 `$convert <point_amount> <from_symbol> <to_symbol>`
      Convert value from one program to another.
      Example: `$convert 1000 HSBC BA`

      \U0001F539 `$help`
      See this message for list of commands. 

      *Always check terms & conditions of each specific point program for latest updates.*     
      '''
      
      #Message to send:
      message = 'Hi, I can help you to convert point value between different travel reward programs.\n**List of commands I can support:**\n>>> {}'.format(command_list)
      
      await channel.send(message)
    break

#Create $help command
@bot.command(name='help', pass_context = True, ignore_extra = False)
async def help(ctx):
  #Command list to display in message
  command_list = '''\
  \U0001F539 `$all`
  List all supported point programs.

  \U0001F539 `$list <program_symbol>`
  List all point programs that are convertible from your chosen point program.
  Example: `$list HSBC`

  \U0001F539 `$convert <point_amount> <from_symbol> <to_symbol>`
  Convert value from one program to another.
  Example: `$convert 1000 HSBC BA`

  \U0001F539 `$help`
  See this message for list of commands.

  *Always check terms & conditions of each specific point program for latest updates.
  Latest update: Feb 2021.*
  '''
  
  #Message to send:
  message = 'Hi, I can help you to convert point value between different travel reward programs.\n**List of commands I can support:**\n>>> {}'.format(command_list)

  await ctx.channel.send(message)

#Create '$all' command:
@bot.command(name='all', ignore_extra = False)
async def all(ctx):

  #Get program list from database, format and save into a list 
  program_list = []
  for row in cur.execute('SELECT point_id, name, symbol FROM Points'):
    program = f'{row[0]}. __{row[1]}__ - {row[2]}'
    program_list.append(program)
  
  #Display each program in a single line
  new_line = '\n'
  display_list = new_line.join(program_list)
  
  #Message to send:
  message = '**All supported point programs & symbols:**\n>>> {}'.format(display_list)

  await ctx.channel.send(message)

#Create '$list <program_symbol>' command:
@bot.command(name='list', ignore_extra = False)
async def list(ctx, program_symbol: to_upper):
  #Get list of all symbols to check user's input:
  symbol_list = []
  for row in cur.execute('SELECT symbol FROM Points'):
    symbol = row[0]
    symbol_list.append(symbol)

  #Check input of users and return error message:
  #If symbol is not in the list:
  if program_symbol not in symbol_list:
    await ctx.channel.send('*Wrong symbol input.\nPlease check again or use `$all` command to see list of symbols.*')
  
  # Run command if input is good:
  else:
    #Get program list from database to display
    program_list = []
    i = 1
    for row in cur.execute('''SELECT p2.name as name, p2.symbol as symbol
    FROM ConvRate c
    INNER JOIN Points p1 ON p1.point_id = c.from_point_id
    INNER JOIN Points p2 ON p2.point_id = c.to_point_id
    WHERE c.conv_rate IS NOT '0' AND p1.point_id IN
    (SELECT point_id FROM Points WHERE symbol = ?)''', (program_symbol,)):
      program = f'{i}. __{row[0]}__ - {row[1]}'
      program_list.append(program)
      i += 1
    
    #Inform user if there's no convertible program
    if not program_list:
      await ctx.channel.send('***{}** is not convertible to any supported points program.*'.format(program_symbol))
    
    #Show a list of convertible programs if exist
    else:
      #Display each program in a single line
      new_line = '\n'
      display_list = new_line.join(program_list)
      
      #Message to send:
      message = '**Convertible point programs for {}:**\n>>> {}'.format(program_symbol, display_list)

      await ctx.channel.send(message)

#Create '$convert <amount> <from_symbol> <to_symbol>' command:
@bot.command(name='convert', ignore_extra = False)
async def convert(ctx, point_amount: int, from_symbol: to_upper, to_symbol: to_upper):
  #Get list of all symbols to check user's input:
  symbol_list = []
  for row in cur.execute('SELECT symbol FROM Points'):
    symbol = row[0]
    symbol_list.append(symbol)

  #Special cases: Check input of users and return messages:
  #Case 1: If symbol is not in the list:
  if (from_symbol not in symbol_list) or (to_symbol not in symbol_list):
    await ctx.channel.send('*Wrong symbol input.\nPlease check again or use `$all` command to see list of symbols.*')

  #Case 2: If converting the same point program
  elif from_symbol == to_symbol:
    message = '**Converted result:**\n {} {} pts = {} {} pts'.format(point_amount, from_symbol, point_amount, to_symbol)
    await ctx.channel.send(message)
  
  #Convert the amount:
  else:
    #Get rate from database
    cur.execute('''SELECT c.conv_rate
      FROM ConvRate c
      INNER JOIN Points p1 ON p1.point_id = c.from_point_id
      INNER JOIN Points p2 ON p2.point_id = c.to_point_id
      WHERE p1.point_id IN
      (SELECT point_id FROM Points WHERE symbol = ?)
      AND p2.point_id IN
      (SELECT point_id FROM Points WHERE symbol = ?)''',(from_symbol, to_symbol))
    
    rate_data = cur.fetchall()
    rate_fraction = rate_data[0][0]
    rate = float(Fraction(rate_fraction))
    
    #Unable to convert if conversion rate = 0
    if rate == 0:
      message = '***{}** cannot be converted to **{}**.\nUse `$list {}` command to see the convertible programs for **{}**.*'.format(from_symbol, to_symbol, from_symbol, from_symbol)
      await ctx.channel.send(message)
    
    #Calculate if conversion rate is not 0
    else:
      if point_amount % 1000 == 0:
        #Calculate converted amount for output. Format with commas as thousands separator
        conv_amount = '{:,}'.format(round((point_amount)*rate))
        point_amount = '{:,}'.format(point_amount)

        #Message to send:
        message = '**Converted result:**\n> {} {} pts = {} {} pts'.format(point_amount, from_symbol, conv_amount, to_symbol)

        await ctx.channel.send(message)
      
      else:
        #Get new point amount for calculation by subtracting the remaining points(since most rewards programs required to convert an amount that is divisible to 1000):
        remaining_points = point_amount % 1000
        point_amount = point_amount - remaining_points
        
        #Calculate converted amount for output.
        #Format numbers with commas as thousands separator
        conv_amount = '{:,}'.format(round((point_amount)*rate))
        point_amount = '{:,}'.format(point_amount)
        
        #Message to send:
        message = '**Converted result:**\n> {} {} pts = {} {} pts\nRemaining {} points: {}'.format(point_amount, from_symbol, conv_amount, to_symbol, from_symbol, remaining_points)

        await ctx.channel.send(message)


#Handle error - Global scope:
@bot.event
async def on_command_error(ctx, error):
  #Inform when user sends wrong command:
  if isinstance(error, commands.CommandNotFound):
    await ctx.channel.send('*Invalid command used.\nUse `$help` for more.*')

#Handle error for $all command:
@all.error
async def all_error(ctx, error):
  #Inform when user inputs too many arguments:
  if isinstance(error, commands.TooManyArguments):
    message = '*Invalid syntax. Do you mean `$all`?*'

    await ctx.channel.send(message)

#Handle error for $help command:
@help.error
async def help_error(ctx, error):
  #Inform when user inputs too many arguments:
  if isinstance(error, commands.TooManyArguments):
    message = '*Invalid syntax. Do you mean `$help`?*'

    await ctx.channel.send(message)

#Handle error for $list command:
@list.error
async def list_error(ctx, error):
  #Inform if lack of arguments:
  if isinstance(error, commands.MissingRequiredArgument):
    message = '*Please specify the point program.\n> __Syntax__: `$list <program_symbol>`\nUse `$help` for more.*'

    await ctx.channel.send(message)
  
  #Inform when user inputs too many arguments:
  if isinstance(error, commands.TooManyArguments):
    message = '*Too many inputs.\n> __Syntax__: `$list <program_symbol>`\nUse `$help` for more.*'

    await ctx.channel.send(message)

#Handle error for $convert command:
@convert.error
async def convert_error(ctx, error):
  #Inform if lack of arguments:
  if isinstance(error, commands.MissingRequiredArgument):
    message = '*Please specify the required inputs.\n> __Syntax__: `$convert <point_amount> <from_symbol> <to_symbol>`\nUse `$help` for more.*'

    await ctx.channel.send(message)

  #Inform when user inputs too many arguments:
  if isinstance(error, commands.TooManyArguments):
    message = '*Too many inputs.\n> __Syntax__: `convert <point_amount> <from_symbol> <to_symbol>`\nUse `$help` for more.*'

    await ctx.channel.send(message)
  
  #Inform for invalid inputs:
  if isinstance(error, commands.UserInputError):  
    message = '*Invalid input(s).\n> __Syntax__:\n> `$convert <point_amount> <from_symbol> <to_symbol>`\n> __Format__:\n> `<point_amount>`: integer\n> `<from_symbol>` & `<to_symbol>`: text\nUse `$help` for more.*'

    await ctx.channel.send(message)

#Keep the bot alive
keep_alive()

#If running code locally, don't need the .env file.
#Just replace 'os.getenv('TOKEN')' with the token
bot.run(os.getenv('TOKEN'))
