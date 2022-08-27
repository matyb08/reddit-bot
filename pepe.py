import requests
import shutil
import os
import html
import mimetypes
import sys
from requests.auth import HTTPBasicAuth
from PIL import Image

# CONFIG
REDDIT_CLIENT_ID = os.environ['REDDIT_CLIENT_ID']
REDDIT_CLIENT_SECRET = os.environ['REDDIT_CLIENT_SECRET']
REDDIT_USERNAME = os.environ['REDDIT_USERNAME']
REDDIT_PASSWORD = os.environ['REDDIT_PASSWORD']
DISCORD_AUTH_KEY = os.environ['DISCORD_AUTH_KEY']
DISCORD_CHANNEL_ID = os.environ['DISCORD_CHANNEL_ID']
DOWNLOADED_ARCHIVE = 'dld.txt'
IM_DIR = 'im/' # PLEASE add a '/' at the end  o_o
# --

# Existence checks
if not os.path.exists(DOWNLOADED_ARCHIVE):
    with open(DOWNLOADED_ARCHIVE, 'w') as dld:
        pass

if not os.path.exists(IM_DIR):
    os.mkdir(IM_DIR)

# Auth
reddit_auth = HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
reddit_data = {
    'grant_type': 'password',
    'username': REDDIT_USERNAME,
    'password': REDDIT_PASSWORD
}
reddit_headers = {
    'User-Agent': 'MyAPI/0.0.1'
}

reddit_response = requests.post('https://www.reddit.com/api/v1/access_token',
                                auth=reddit_auth,
                                data=reddit_data,
                                headers=reddit_headers
                                )

reddit_token = reddit_response.json()['access_token']
reddit_headers['Authorization'] = f'bearer {reddit_token}'

# Query
reddit_response = requests.get('https://oauth.reddit.com/r/' + 'greentext/top?t=day', # add limit=100 to get 100 posts (100 is max per request)
                               headers=reddit_headers
                               ) # Request for r/greentext/ best of the day

child_index = 0
while True:
    # Get nth post
    post_data = reddit_response.json()['data']['children'][child_index]['data']
    post_url = 'https://www.reddit.com' + post_data['permalink']
    title = html.unescape(post_data['title'])
    nsfw = post_data['over_18']

    with open('dld.txt', 'r+') as dld:
        foiul_name = ''

        if post_url not in dld.read():
            # Gallery post
            if 'is_gallery' in post_data:
                images = [] # Will contain Image objects of all images
                extension = ''

                for i, img in enumerate(post_data['gallery_data']['items']):
                    im_id = img['media_id']
                    mime = post_data['media_metadata'][im_id]['m']

                    # Exception for 'image/jpg' (because not jpEg)
                    if mime == 'image/jpg':
                        extension = '.jpg'
                    else:
                        extension = mimetypes.guess_extension(mime)

                    url = f'https://i.redd.it/{im_id}{extension}'
                    response = requests.get(url, stream=True)

                    foiul_name = f'{IM_DIR}{i}-{title}{extension}'

                    with open(foiul_name, 'wb') as im:
                        shutil.copyfileobj(response.raw, im)

                    images.append(Image.open(foiul_name))

                # Merge
                merged_width = max([image.width for image in images])
                merged_height = sum([image.height for image in images])
                merged_image = Image.new('RGB', (merged_width, merged_height), (255, 255, 255))

                sum_of_heights_till_now = 0
                for image in images:
                    merged_image.paste(image, (int((merged_width - image.width) / 2), sum_of_heights_till_now))
                    sum_of_heights_till_now += image.height

                if nsfw:
                    foiul_name = f'{IM_DIR}SPOILER_{title}{extension}'
                else:
                    foiul_name = f'{IM_DIR}{title}{extension}'

                merged_image.save(foiul_name)

                # Clean up
                for image in images:
                    os.remove(image.filename)


            # Single image post
            else:
                url = post_data['url']
                response = requests.get(url, stream=True)

                if nsfw:
                    foiul_name = f'{IM_DIR}SPOILER_{title}.{url.split(".")[-1]}'
                else:
                    foiul_name = f'{IM_DIR}{title}.{url.split(".")[-1]}'

                with open(foiul_name, 'wb') as im:
                    shutil.copyfileobj(response.raw, im)


            # Send
            with open(foiul_name, 'rb') as f:
                discord_files = { '0': f }
                discord_header = { 'authorization': DISCORD_AUTH_KEY }
                discord_payload = { 'content': title }

                discord_request = requests.post(f'https://discord.com/api/v9/channels/{DISCORD_CHANNEL_ID}/messages',
                                                files=discord_files,
                                                headers=discord_header,
                                                data=discord_payload
                                                )

                if not discord_request.ok:
                    sys.stderr.write(f'{discord_request.reason} [{discord_request.status_code}]\n')
                    break


            dld.write(post_url + '\n')

            if nsfw:
                os.rename(foiul_name, foiul_name.replace('SPOILER_', ''))

            break

        else:
            child_index += 1
            continue
