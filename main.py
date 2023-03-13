import sqlite3, json, functools, typing, asyncio, traceback, os

# Import env
env = {}
with open('.env', 'r') as file:
    for line in file:
        name, value = line.strip().split('=')
        env[name] = value

# Import config.json
with open('config.json', 'r') as file:
    config = json.load(file)

if not os.path.exists(config["convo_folder"]):
    os.makedirs(config["convo_folder"])

class Database:
    def __init__(self, dbname: str):
        self.dbname = dbname
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.dbname)
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()

# Initialize Database
with Database(config["db_file"]) as db:
    db.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userid INTEGER NOT NULL,
        channelid INTEGER NOT NULL,
        role TEXT NOT NULL DEFAULT 'Assistant',
        open INTEGER NOT NULL DEFAULT 1
    )''')
#conversationdata TEXT NOT NULL,

# Database Shortcuts
def getConvo(channelid):
    with Database(config["db_file"]) as db:
        db.execute("SELECT * FROM conversations WHERE channelid = ?", (channelid,))
        row = db.fetchone()
        if row is not None:
            return {
                "id": row[0],
                "userid": row[1],
                "channelid": row[2],
#                "conversationdata": json.loads(row[3]),
                "role": row[3]
            }
        else:
            return None
        
def isOpen(channelid):
    with Database(config["db_file"]) as db:
        db.execute("SELECT open FROM conversations WHERE channelid = ?", (channelid,))
        row = db.fetchone()
        if row is not None:
            return bool(row[0])
        else:
            return None

# Handles asynchroneous functions without the use of async/await
# This is to prevent the bot's "heartbeat" from being interrupted from long tasks
def to_thread(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        wrapped = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, wrapped)
    return wrapper

# Error Handling at its finest (wrong)
def errHandler(e):
    print(f"Error occured while asking ChatGPT: {e}\n\n{traceback.format_exc()}") # To Console
    return ":warning: An error occured. The error has been logged." # To Discord
    # Alternatively, you can use the following line to send the error to the channel.
    # ...although this could reveal sensitive information (such as the execution path)
    #return f":warning: {e}\n\n```{traceback.format_exc()[:1900]}```" # To Discord

# Initialize Discord
import discord
from discord.ext import commands
from discord import app_commands
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="gpt!", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    synced = await tree.sync() # Probably not a good idea if the bot restarts frequently
    print(f"Bot is ready! {len(synced)} commands synced.")

from revChatGPT.V3 import Chatbot
chatbot = Chatbot(api_key=env["openai_api_key"])

async def gptAddToConvo(query: str, role: str, convo_id: str):
    return chatbot.add_to_conversation(query, role, convo_id)

async def gptAsk(query: str, role: str, convo_id: str):
    return chatbot.ask(query, role, convo_id)
    

async def discordAskGPT(msg: discord.Message | discord.InteractionMessage, query: str, role: str = "assistant", base_prompt: str = config["main_base_prompt"], interact: discord.Interaction = None, usr: discord.User = None):
    # I'm sorry
    try:
        if interact != None:
            guild = interact.guild
            channel = interact.channel
            userid = interact.user.id
        else:
            guild = msg.guild
            channel = msg.channel
            userid = msg.author.id

        try:
            chatbot.load(f"conversations/{guild.id}-{channel.id}.json", str(channel.id))
        except:
            pass
        convo_data = getConvo(channel.id)

        # Create new conversation data
        if convo_data == None:
            convo_data = {
                "userid": userid,
                "channelid": channel.id,
                "role": role,
#                "conversationdata": []
            }
            chatbot.reset(str(channel.id), base_prompt)
        
        if (config["bot_knows_usernames"] == True) and (usr != None):
            query = f"{usr.display_name}: {query}"

#        convo_data["conversationdata"].append(query)
        
        response = await gptAsk(query, role, str(channel.id))
        remaining = []
        lq = len(query) + 3
        if len(response) >= (2000-lq):
            remaining = [response[(2000-lq):(3999-lq)], response[(4000-lq):(5999-lq)]] # this sucks

        await msg.edit(content=f"`{query}`\n{response[:(1999-lq)]}")
        for remainder in remaining:
            if remainder != "":
                await channel.send(remainder)

#        conversationdata_json = json.dumps(convo_data["conversationdata"])

        with Database(config["db_file"]) as db:
            db.execute("SELECT EXISTS(SELECT 1 FROM conversations WHERE channelid = ?)", (channel.id,))
            row_exists = bool(db.fetchone()[0])
            if row_exists:
                """db.execute("UPDATE conversations SET conversationdata = ? WHERE channelid = ?",
                    (conversationdata_json, channel.id)
                )"""
                pass
            else:
                db.execute("INSERT INTO conversations (userid, channelid, role) VALUES (?, ?, ?)",
                    (userid, channel.id, role) #conversationdata_json
                )

        chatbot.save(f"conversations/{guild.id}-{channel.id}.json", str(channel.id))

    except Exception as e:
        await msg.edit(content=errHandler(e))

class ThreadModal(discord.ui.Modal, title="Create a conversation with ChatGPT"):
    thread_name = discord.ui.TextInput(
        label="Title of the thread (Optional)",
        placeholder="the conversation of all time",
        max_length=30,
        style=discord.TextStyle.short,
        required=False
    )
    thread_base_prompt = discord.ui.TextInput(
        label="Base prompt (Optional, not shown)",
        placeholder="You are ChatGPT, a large language model trained by OpenAI. Respond conversationally.",
        max_length=100,
        style=discord.TextStyle.short,
        required=False
    )
    thread_input = discord.ui.TextInput(
        label="Prompt",
        placeholder="Check out https://prompts.chat/",
        style=discord.TextStyle.paragraph,
        max_length=1900,
        required=True
    )
    async def on_submit(self, interaction: discord.Interaction):
        threadName = self.thread_name.value
        if threadName == "":
            threadName = f"{interaction.user.display_name}'s chat"
        await interaction.response.send_message(f"`{self.thread_input.value}`\nPlease run the `/ask <prompt>` command to continue the conversation!")
        msg = await interaction.original_response()
        try:
            thread = await msg.create_thread(name=threadName, auto_archive_duration=1440)
            thread_msg = await thread.send("Please wait a moment while I generate a response...")
            await discordAskGPT(thread_msg, self.thread_input.value, self.thread_base_prompt.value, usr=interaction.user)
        except Exception as e:
            await msg.edit(content=errHandler(e))

@tree.command(name="createchat", description="Create a ChatGPT conversation! (A pop-up will show up)")
async def interactionCreateChat(interaction: discord.Interaction):
    await interaction.response.send_modal(ThreadModal())

@tree.command(name="ask", description="Prompt ChatGPT a question. (In ChatGPT Threads only)")
@app_commands.describe(text = "Enter your prompt to ask ChatGPT")
async def interactionAskChatGPT(interaction: discord.Interaction, text: str):
    if (interaction.channel.type != discord.ChannelType.public_thread):
        return await interaction.response.send_message("This command can only be used in ChatGPT-connected threads!", ephemeral=True)
    if text == "":
        return await interaction.response.send_message("No input prompt given.", ephemeral=True)
    
    await interaction.response.send_message("Please wait a moment while I generate a response...")
    return await discordAskGPT(await interaction.original_response(), text, interact=interaction, usr=interaction.user)

bot.run(env["bot_token"])
