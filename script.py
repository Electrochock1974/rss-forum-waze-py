import requests
import json
import feedparser
import html
import os
import time
from bs4 import BeautifulSoup

rss_urls = ["https://www.waze.com/forum/app.php/feed/forum/1250", "https://www.waze.com/forum/app.php/feed/forum/1255"]
token = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
threads_db = {}
tag_ids = {
    "Fermetures pour travaux": "1126645034024964257",
    "Fermetures Événementielles": "1126946064965062776"
}

def get_tag_id_from_title(title):
    for keyword, tag_id in tag_ids.items():
        if title.startswith(keyword):
            return tag_id
    return None

def create_discord_thread_and_message(thread_title, thread_content, link, tag_id):
    discord_url = "https://discord.com/api/v10/channels/1126177475962089492/threads"
    payload = {
        "name": thread_title,
        "auto_archive_duration": 60,
        "message": {
            "content": thread_content
        },
        "applied_tags": [tag_id]
    }
    headers = {
        "Authorization": "Bot " + token,
        "Content-Type": "application/json"
    }
    response = requests.post(discord_url, headers=headers, data=json.dumps(payload))
    if response.status_code == 201:
        print("Thread créé avec succès et message envoyé.")
        thread_id = response.json()['id']
        threads_db[thread_title] = {"thread_id": thread_id, "title": thread_title, "message": thread_content, "replies": [link]}
        with open('threads.json', 'w') as f:
            json.dump(threads_db, f)
    else:
        print(f"Une erreur est survenue : {response.status_code}, {response.text}")

def respond_discord_message(thread_id, message, link, thread_title):
    url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
    payload = {"content": message}
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        print("Message envoyé avec succès !")
        threads_db[thread_title]['replies'].append(link)
        with open('threads.json', 'w') as f:
            json.dump(threads_db, f)
    else:
        print(f"Erreur lors de l'envoi du message : {response.status_code}, {response.text}")

while True:
    if os.path.isfile('threads.json') and os.path.getsize('threads.json') > 0:
        with open('threads.json', 'r') as f:
            threads_db = json.load(f)
    for rss_url in rss_urls:
        feed = feedparser.parse(rss_url)
        last_entry = feed.entries[0]
        title = last_entry.title.split(' - ', 1)[-1] if ' - ' in last_entry.title else last_entry.title
        if "Re: " in title:
            title = title.replace("Re: ", "")
        link = last_entry.link
        content = BeautifulSoup(last_entry.content[0]['value'], "html.parser").get_text()
        message = f"Nouveau message sur le forum : \n\n{html.unescape(content)} \n\n Pour répondre à ce message, cliquez sur le lien <{link}>"

        if title in threads_db:
            if link not in threads_db[title]['replies']:
                respond_discord_message(threads_db[title]['thread_id'], message, link, title)
            else:
                print("Cette entrée a déjà été traitée.")
        else:
            tag_id = get_tag_id_from_title(title)
            if tag_id:
                create_discord_thread_and_message(title, message, link, tag_id)
            else:
                print("Erreur : Impossible de trouver un tag correspondant pour le titre du thread.")
    time.sleep(1)
