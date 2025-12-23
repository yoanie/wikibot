import discord
import os
import requests
import re
import datetime

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

USER_AGENT = 'wikibot, a python program (made by yoanie)'
TEXT_LIMIT = 2000
EMOJI_LEFT = '⬅️'
EMOJI_RIGHT = '➡️'

cache = {}
messageController = {
}  # index:discMessageId {messageObj, titleString, currPageIndex}


def get_article_text(prompt):
    params: dict[str, str] = {
        'action': 'query',
        'titles': prompt,
        'prop': 'extracts',
        'format': 'json'
    }
    response = requests.get('https://en.wikipedia.org/w/api.php',
                            headers={
                                'Authorization':
                                os.getenv('WIKIBOT_ACCESSTOKEN'),
                                'User-Agent': USER_AGENT
                            },
                            params=params)

    # print(response.json())
    json_data = list(response.json()['query']['pages'].values())[0]
    # print(list(json_data))

    return get_formatted_fulltext_from_json(json_data)


def get_featured_article_title(date):
    print("getting query")
    params: dict[str, str] = {
        'action': 'query',
        'prop': 'extracts',
        'format': 'json'
    }

    response = requests.get(
        'https://api.wikimedia.org/feed/v1/wikipedia/en/featured/' + date,
        headers={
            'Authorization': os.getenv('WIKIBOT_ACCESSTOKEN'),
            'User-Agent': USER_AGENT
        },
        params=params)

    # print(response.json()['tfa'])
    title = response.json()['tfa']['titles']['normalized']
    print(title)

    return title


def get_formatted_fulltext_from_json(json_data):
    if 'extract' not in json_data:
        return ''

    data = json_data['extract']

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

    if message.content[:5] == '$page':
        arg0 = re.sub(r"^\$page(\d*)\D+$", r"\1", message.content)
        if (arg0 == ''):
            pagenum = 1
        else:
            pagenum = int(arg0)

        arg1 = message.content[6 + len(arg0):]
        page = re.sub(r'^\s+|\s+$|\s+(?=\s)', "", arg1)

        await send_specific_page_as_message(message.channel, page, pagenum - 1)

    if message.content.startswith('$article'):
        arg1 = message.content[9:]
        page = re.sub(r'^\s+|\s+$|\s+(?=\s)', "", arg1)

        await send_specific_page_as_message(message.channel, page, 0)

    if message.content.startswith('$featured') or message.content.startswith(
            '$featuredarticle') or message.content.startswith('$fa'):
        today = datetime.datetime.now()
        date = today.strftime('%Y/%m/%d')

        arg1 = re.findall(r'^.+ ([ \S]*)', message.content)
        print("arg1 is "+str(arg1))
        if len(arg1) != 0:
            date = arg1[0]
        print('date is '+str(date))

        title = f'{get_featured_article_title(date)}'

        if title == "":
            await message.channel.send(
                "`it seems the date you entered (\"{date}\") isn't valid, or there isn't an entry for this date!`\n`be sure to check that your date is in YYYY/MM/DD format!`"
            )
            return

        await send_specific_page_as_message(message.channel, title, 0)


async def send_specific_page_as_message(channel, title, n):
    if title == "":
        await channel.send(
            "`you didn't set an article to search for!`\n`if you want a suggestion of what to search, try the article titled \"Ray cat\"! it's my personal favorite.`"
        )
        return
    if get_article_text(title) == "":
        await channel.send(
            f"`sorry, it seems that the article \"{title}\" didn't have an entry in Wikipedia, or that the page was blank. maybe you made a typo?`"
        )
        return

    if title not in cache:
        cache[title] = [get_article_text(title), get_article_image(title)]
    #cache[page] = [get_article_text(page), get_article_image(page)]
    summary, imageUrl = cache[title]

    # for displaying the very first title thing
    titleUnderscore = title.replace(" ", "_")
    await channel.send(
        f"# [{title}](<https://en.wikipedia.org/wiki/{titleUnderscore}>)\n[[image]]({imageUrl})\n"
    )

    # seperate full text by pages
    pages = partition_pages_from_text(summary, TEXT_LIMIT - 20)
    # print(pages)

    # send message of only the page specified
    if n + 1 > len(pages):
        currIndex = len(pages) - 1
    elif n < 0:
        currIndex = 0
    else:
        currIndex = n

    messageSent = await channel.send(
        f'{pages[currIndex]}\n⎯\nPage: {format_number_for_discord(currIndex+1)}/{format_number_for_discord(len(pages))}'
    )
    await messageSent.add_reaction(EMOJI_LEFT)
    await messageSent.add_reaction(EMOJI_RIGHT)

    # print(messageSent)
    messageController[messageSent.id] = [messageSent, title, currIndex]


def format_number_for_discord(number):
    if number < 10:
        return f'`0{number}`'
    return f'`{number}`'


def partition_pages_from_text(text, charlimit):
    pages = []
    pointer = 0
    while pointer < len(text):
        #print(summary[pointer:pointer+charlimit])
        try:
            temp = charlimit - text[pointer:pointer +
                                    charlimit][::-1].index('.')
        except:
            """print(
                "def partition_pages_from_text: couldnt find period, so defaulting..."
            )"""
            temp = charlimit
        else:
            temp = charlimit - text[pointer:pointer +
                                    charlimit][::-1].index('.')

        pages.append(text[pointer:pointer + temp])
        print(len(text[pointer:pointer + temp]))
        pointer += temp + 1
        if (text[pointer:pointer + 1] == ' '):
            pointer += 1

    return pages


@client.event
async def on_raw_reaction_add(payload):
    # print(payload)
    if payload.user_id == payload.message_author_id:
        return
    print("reaction reacted on bot message!")

    if (payload.emoji.name != EMOJI_LEFT
            and payload.emoji.name != EMOJI_RIGHT):
        return

    print(payload.message_id)
    print(messageController[payload.message_id])

    # seperate full text by pages
    summary = cache[messageController[payload.message_id][1]][0]
    # print(summary)
    pages = partition_pages_from_text(summary, TEXT_LIMIT - 20)

    print(payload.emoji)
    newPageIndex = 0
    if payload.emoji.name == EMOJI_LEFT:
        print('user reacted left')
        newPageIndex = (messageController[payload.message_id][2] - 1 +
                        len(pages)) % len(pages)
    elif payload.emoji.name == EMOJI_RIGHT:
        print('user reacted right')
        newPageIndex = (messageController[payload.message_id][2] + 1 +
                        len(pages)) % len(pages)

    messageController[payload.message_id][2] = newPageIndex

    print(newPageIndex)
    # print(pages)
    # print(pages[newPageIndex])

    messag = messageController[payload.message_id][0]
    await messag.edit(
        content=
        f'{pages[newPageIndex]}\n⎯\nPage: {format_number_for_discord(newPageIndex+1)}/{format_number_for_discord(len(pages))}'
    )
    #f'{pages[currIndex]}\n⎯\nPage: {format_number_for_discord(currIndex+1)}/{format_number_for_discord(len(pages))}'


# discord bot token
client.run(os.getenv('WIKITOKEN'))
