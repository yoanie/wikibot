import discord
import os
import requests
import re

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
TEXT_LIMIT = 2000 - 6
EMOJI_LEFT = '⬅️'
EMOJI_RIGHT = '➡️'

cache = {}
messageController = {}  # index:discMessageId {titleString, currPageIndex}


def get_random_article(prompt):
    params: dict[str, str] = {
        'action': 'query',
        'titles': prompt,
        'prop': 'extracts',
        'format': 'json'
    }
    response = requests.get('https://en.wikipedia.org/w/api.php',
                            headers={'User-Agent': 'python'},
                            params=params)

    # print(response)
    json_data = response.json()
    # print(json_data['query']['pages'].values())

    data = list(json_data['query']['pages'].values())[0]['extract']

    quoteBold = re.sub(r"<\/?(?:b|strong)>", "**", data)
    quoteBoldItalic = re.sub(r"<\/?(?:i|em)( [^>]+)?>", "*", quoteBold)
    quoteBoldItalicDel = re.sub(r"<\/?del>", "~~", quoteBoldItalic)
    quoteBoldItalicDelIns = re.sub(r"<\/?ins>", "__", quoteBoldItalicDel)

    quote0 = re.sub(r"<h2( [^>]+)>", "## ", quoteBoldItalicDelIns)
    quote1 = re.sub(r"<h3( [^>]+)>", "### ", quote0)
    quote2 = re.sub(r"&amp;", "&", quote1)
    quote = re.sub(r"(<.+?>>[^<]+?<.+?>)|(<.+?>)", "", quote2)

    quoteFinal = f"{quote}"

    return quoteFinal


def get_article_image(prompt):
    params: dict[str, str] = {
        'action': 'query',
        'titles': prompt,
        'prop': 'images',
        'imlimit': '1',
        'format': 'json'
    }
    response = requests.get('https://en.wikipedia.org/w/api.php',
                            headers={'User-Agent': 'python'},
                            params=params)

    json_data = response.json()
    print(json_data)

    data = json_data['continue']['imcontinue'].split('|')[1]
    print(data)

    imageUrl = f"https://en.wikipedia.org/wiki/Special:FilePath/{data}"
    return imageUrl


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    if message.content.startswith('$page'):
        page = 'Ray cat'

        if page not in cache:
            cache[page] = [get_random_article(page), get_article_image(page)]
        #cache[page] = [get_random_article(page), get_article_image(page)]
        summary, imageUrl = cache[page]

        # for displaying the very first title thing
        pageUnderscore = page.replace(" ", "_")
        await message.channel.send(
            f"# [{page}](<https://en.wikipedia.org/wiki/{pageUnderscore}>)\n[[image]]({imageUrl})\n"
        )

        # seperate full text by pages
        pages = partition_pages_from_summary(summary)

        # send message of only the page specified
        currIndex = 0
        messageSent = await message.channel.send(f'{pages[currIndex]}')
        await messageSent.add_reaction(EMOJI_LEFT)
        await messageSent.add_reaction(EMOJI_RIGHT)

        # print(messageSent)
        messageController[messageSent.id] = [pages, currIndex]


def partition_pages_from_summary(summary):
    pages = []
    pointer = 0
    while pointer < len(summary):
        #print(summary[pointer:pointer+TEXT_LIMIT])
        try:
            temp = TEXT_LIMIT - summary[pointer:pointer +
                                        TEXT_LIMIT][::-1].index('.')
        except:
            temp = TEXT_LIMIT
        else:
            temp = TEXT_LIMIT - summary[pointer:pointer +
                                        TEXT_LIMIT][::-1].index('.')
        pages.append(summary[pointer:pointer + temp])
        print(len(summary[pointer:pointer + temp]))
        pointer += temp + 1
        if (summary[pointer:pointer + 1] == ' '):
            pointer += 1

    return pages


@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == "bot_ID":
        return

    print(payload.emoji)
    if payload.emoji == EMOJI_LEFT:
        print('user reacted')

    if payload.emoji == EMOJI_RIGHT:
        print('user reacted')


# discord bot token
client.run(os.getenv('WIKITOKEN'))
