# ThreadGPT
"oh wow, another ChatGPT Discord Bot"

This utilizes [revChatGPT](https://github.com/acheong08/ChatGPT/) to run a fairly simple Discord Bot that can split up conversation into threads. Hence the name! (im a genius)

## Configuration
Edit `.env` accordingly.
`.env` contains your Bot token and your [OpenAI API key](https://platform.openai.com/account/api-keys). Example:
```env
bot_token=cWhhcj8h...
openai_api_key=sk_d2VlZA...
```
`config.json` contains various settings, such as file/folder locations for storing conversations and the base-prompt.  
You can also set `"bot_knows_usernames"` to `true` so that the bot knows the nickname (or username if no nickname is set) of the user the bot is talking to.
```json
{
    "db_file": "convos.db",
    "convo_folder": "conversations",
    "main_base_prompt": "You are ChatGPT, a large language model trained by OpenAI. Respond conversationally and adjust to the user's language.",
    "bot_knows_usernames": false
}
```

## Usage
The bot has two commands as of now:
```
/createchat - Opens up a pop-up asking for a prompt, then creates a thread assosciated with the converstaion generated.
/ask <prompt> - Ask with a prompt in a chat.
```

## Notice of lacking functionality or issues
- There is currently no implementation of disallowing a conversation to continue.
- There is no shortcut-command for /createchat. I'll consider making that sometime soon.
- This is currently using a specific version of revChatGPT. The newest version (newer than 3.3.1) has a different implementation of the save/load function, which I personally am a little confused over of how to implement it properly.