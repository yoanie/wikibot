import discord
import os
import requests
import json
import re
import time

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
TEXT_LIMIT = 2000


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

        summary = get_random_article(page)
        imageUrl = get_article_image(page)

        pageUnderscore = page.replace(" ", "_")
        await message.channel.send(
            f"# [{page}](<https://en.wikipedia.org/wiki/{pageUnderscore}>)\n[[image]]({imageUrl})\n"
        )
        
        pages = []
        pointer = 0
        while pointer < len(summary):
            #print(summary[pointer:pointer+TEXT_LIMIT])
            temp = TEXT_LIMIT - summary[pointer:pointer +
                                        TEXT_LIMIT][::-1].index('.')
            pages.append(summary[pointer:pointer + temp])
            print(len(summary[pointer:pointer + temp]))
            pointer += temp + 1
            if (summary[pointer:pointer + 1] == ' '):
                pointer += 1

        for i in range(0, len(pages), 1):
            await message.channel.send(f'{pages[i]}')
        #length = len(summary)
        #for i in range(0, length, TEXT_LIMIT):
        #    await message.channel.send(f'{summary[i:i+TEXT_LIMIT]}')


# i think this is the discord bot token not the wikipedia one
client.run(os.getenv('WIKITOKEN'))
