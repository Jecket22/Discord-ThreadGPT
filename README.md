# ThreadGPT
"oh wow, another ChatGPT Discord Bot"

This utilizes [revChatGPT](https://github.com/acheong08/ChatGPT/) to run a fairly simple Discord Bot that can split up conversation into threads. Hence the name! (im a genius)

## Configuration
Edit `.env` and `chatgpt_config.json` accordingly.
`.env` contains your bot token. Example:
```env
bot_token=cWhhcj8h...
must_mention_bot_in_convos=true
```
`chatgpt_config.json` contains the session/access tokens. Example:
```json
{
    "session_token": "eyYmFsbHM...",
    "access_token": "eybnV0cw...",
    "paid": false
}
```
Said tokens can be found in the cookies/api (check the config file). You can keep the `paid` value to `false` as ChatGPT Plus *by default* currently uses `text-davinci-002-render-sha`, which is also available to free users.

You can also provide "email" and "password" although I don't recommend it unless you're lazy / using this rarely

## Usage
The bot has two commands as of now:
```
/chatgpt - Opens up a pop-up asking for a prompt, then creates a thread assosciated with the converstaion generated.
/removeconvo - Removes the conversation in a thread and locks the thread. This only removes the conversation on ChatGPT's side so that the conversation cannot be continued.
```
You can continue the converstaion in a thread by mentioning the Bot following with another prompt.

## Known issues/lacking features
- There's no database. This is a fairly rushed code suited for just my needs, so I stored the converstaion data inside a message for the time being.
- Edited messages are not recognized, meaning you can only correct your prompts by re-prompting.
- Replying to the bot's message is also not recognized.
- Anyone can remove a conversation. There's no checking of who created a conversation. Whilst the previous messages are kept, this basically removes the ability to continue a conversation in a thread.
- Conversation data is stored in the first pinned message. As such, the bot will only respond if the first pinned message contains the conversation data.
- Currently only one generation at a time is allowed. This is a general limitation of ChatGPT but in case if you want to try anyway, you won't get very far.