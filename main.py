import datetime, traceback, json, functools, typing, asyncio

# Handles asynchroneous functions without the use of async/await
# This is to prevent the bot's "heartbeat" from being interrupted from long tasks
def to_thread(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        wrapped = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, wrapped)
    return wrapper

from revChatGPT.V1 import Chatbot

@to_thread
def gptAsk(query: str, convo_id: str, parent_id: str):
    return chatbot.ask(query, convo_id, parent_id)

@to_thread
def gptDeleteConversation(convo_id: str):
    chatbot.delete_conversation(convoid=convo_id)

# Handles environment variables. Who needs dotenv when you can just do this?
env = {}
with open('.env', 'r') as file:
    for line in file:
        name, value = line.strip().split('=')
        env[name] = value

# Add intents and some variables
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.dm_messages = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='gpt!', intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    print("Bot is running!")
    await tree.sync() # Probably not a good idea if the bot restarts frequently - this function is pretty slooow and could be resource intensive

# Error Handling at its finest (wrong)
def errHandler(e):
    print(f"Error occured while asking ChatGPT: {e}\n\n{traceback.format_exc()}")
    return ":warning: An error occured. The error has been logged."
    # Alternatively, you can use the following line to send the error to the channel.
    # ...although this could reveal sensitive information (such as the execution path)
    #return f":warning: {e}\n\n```{traceback.format_exc()}```"

# ChatGPT related functions and commands
chatbot = Chatbot(json.load(open("chatgpt_config.json")))

# Function that processes the prompt and edits the message accordingly
async def discordAskGPT(msg: discord.Message, query: str, threadName = None):
    # I'm sorry
    try:
        channel = msg.channel
        # We store the conversation ID and parent ID in a pinned message.
        # This is arguably not the best solution, but I was too lazy to implement a database...
        curPins = await channel.pins()
        # If there are no pins, then we assume this is not a ChatGPT thread.
        if len(curPins) == 0:
            await msg.edit(content="Not a valid ChatGPT thread.")
        # pre-defined convoData in case the pinned message is not a valid JSON string
        # None is used to indicate that the conversation is new
        convoData = {"conversation_id": None, "parent_id": None}
        try:
            convoData = json.loads((await channel.pins())[0].content.split("||")[1])
        except ValueError:
            pass #h
        
        # Removes the bot's mention from the query. Leading whitespace is automatically removed by ChatGPT.
        # update: I was wrong
        query = query.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "")
        if query[0] == " ": query = query[1:]


        response = await gptAsk(query, convoData["conversation_id"], convoData["parent_id"])
        # Pre-definition and failsafe in case the API returns an empty response
        trucnated = "No answer received! ChatGPT may be having issues or the prompt is malformed.\n<https://status.openai.com>"
        # More pre-defined variables
        convo_id = None
        parent_id = None
        remaining = []

        # Once we get our response, we iterate through it and send it to the channel.
        for index, data in enumerate(response):
            # Set the message to the truncated message. Appended the "..." to indicate that the bot is still working.
            # Maybe I should use Discord's typing indicator instead? No clue how to implement that though.
            trucnated = data["message"][:1995] + "(...)"

            # If the message is too long, we send the first 2000 characters and store the rest aside.
            if len(trucnated) >= 1995:
                # If I am correct, the maximum message length that can be generated is 4096 characters.
                # Discord's message limit is 2000 for non-nitro users, so we split the message into 3 parts if needed.
                remaining = [data["message"][2000:4000], data["message"][4000:4096]] # this sucks
            # To prevent the bot from being rate-limited, we send a message every few words.
            # Since this is a live chat, we don't want to send the entire message at once.
            # ...or well, that's how ChatGPT works, so I'll keep it that way.
            elif index % 50 == 10: # Edit the message early so that the user knows that the bot is generating a response.
                await msg.edit(content=trucnated)

            # Call me dumb but is there a better way of doing this
            trucnated = data["message"][:2000]
            convo_id = data["conversation_id"]
            parent_id = data["parent_id"]

        # Once done, we edit the message without the "..." and send the remaining text if needed.
        await msg.edit(content=trucnated)
        for remainder in remaining:
            if remainder != "":
                await msg.channel.send(remainder)
        convoData = json.dumps({"conversation_id": convo_id, "parent_id": parent_id})

        # Edit the pinned message to store the conversation ID and parent ID.
        await (await channel.pins())[0].edit(content=f"||{convoData}||")
        # If a thread name is provided, we change the conversation's title.
        # This is only visible on the ChatGPT website, but I thought "eh why not"
        if threadName != None:
            chatbot.change_title(convo_id, threadName)
    except Exception as e:
        await msg.edit(content=errHandler(e))

# Function that deletes the conversation of a thread
# I should probably remake this function
async def discordRemoveConversation(msg: discord.Message):
    channel = msg.channel
    # check if the channel is a thread
    if channel.type != discord.ChannelType.public_thread:
        await msg.edit(content="This command can only be used in threads.")
    try:
        # Since we store the conversation ID in a pinned message, we need to get the pinned message.
        pins = await channel.pins()
        if len(pins) == 0:
            return await msg.edit(content="Not a valid ChatGPT thread.")
        # pre-defined convoData
        convoData = None
        # Check if the first pinned message contains the conversation data, otherwise return.
        try:
            convoData = json.loads(pins[0].content.split("||")[1])
        except ValueError:
            return await msg.edit(content="Not a valid ChatGPT thread.")
        
        # Delete the conversation (if not deleted yet), the pinned message, and lock the thread.
        await gptDeleteConversation(convoData["conversation_id"])
        await pins[0].delete()
        await msg.edit(content="OK, the conversation has been removed.")
        if type(channel) == discord.Thread:
            await channel.edit(locked=True, archived=True)
    except Exception as e:
        await msg.edit(content=errHandler(e))

# Handles the command to prompt ChatGPT
# This creates a pop-up with a text input, and creates a thread afterwards
class ThreadModal(discord.ui.Modal, title="Ask ChatGPT"):
    thread_name = discord.ui.TextInput(
        label="Title of the conversation (Optional)",
        placeholder="conversation of all time",
        max_length=30,
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
        now = datetime.datetime.now()
        threadName = self.thread_name.value
        if threadName == "":
            # There used to be parameter that allowed me to auto-generate a conversation name, but it's commented out for whatever reason...
            threadName = f"{interaction.user.display_name}'s chat"
        await interaction.response.send_message(f"`{self.thread_input.value}`\nPlease mention <@{bot.user.id}> in the Thread, followed by another prompt, to continue the conversation.")
        msg = await interaction.original_response()
        try:
            thread = await msg.create_thread(name=threadName, auto_archive_duration=1440)
            thread_msg = await thread.send("Please wait a moment while I generate a response...")
            newPin = await thread.send("||Creating conversation...||")
            await newPin.pin()
            await discordAskGPT(thread_msg, self.thread_input.value, threadName)
        except Exception as e:
            await msg.edit(content=f":warning: {e}```{traceback.format_exc()}```")

@tree.command(name="chatgpt", description="Ask ChatGPT a question! (A pop-up will show up)")
async def chatgpt(interaction: discord.Interaction):
    await interaction.response.send_modal(ThreadModal())

@tree.command(name="removeconvo", description="Remove a conversation from ChatGPT. Only works in threads.")
async def removeconvo(interaction: discord.Interaction):
    await interaction.response.send_message(f"Alright, deleting the conversation...")
    await discordRemoveConversation(await interaction.original_response())

@bot.event
async def on_message(message: discord.Message):
    # a couple of checks to make sure that the bot only responds in threads
    if message.author.bot: return
    if type(message.channel) == discord.DMChannel: return
    if env["must_mention_bot_in_convos"] == "true":
        if not bot.user.mentioned_in(message): return
    if message.mention_everyone: return
    if (message.channel.type != discord.ChannelType.public_thread): return
    msg = await message.channel.send("Please wait a moment while I generate a response...")
    await discordAskGPT(msg, message.content)

bot.run(env["bot_token"])