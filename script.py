#!/usr/bin/env python3

# Importation des bibliothèques nécessaires
import requests
import json
import feedparser
import html
import os
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import dateutil.parser

# Liste des URL RSS à surveiller
rss_urls = ["https://www.waze.com/forum/app.php/feed/forum/1250", "https://www.waze.com/forum/app.php/feed/forum/1255"]

# Token pour l'authentification sur Discord
token = "MTEyNjQxMjkwMTMxNDQ3NDEwNQ.GTzWEd.g967c0D-Aro_yTYCQmWxrgs4JJ4xRuQniIOc1g"

# Initialisation de la base de données des fils de discussion (threads)
threads_db = {}

# Correspondance des catégories et des tags pour les messages Discord
tag_ids = {
    "Fermetures pour travaux": "1126645034024964257",
    "Fermetures Événementielles": "1126946064965062776"
}

# Fonction pour récupérer le tag id correspondant à la catégorie
def get_tag_id_from_category(category):
    return tag_ids.get(category, None)

# Fonction pour simplifier le titre des entrées
def simplify_title(title):
    for prefix in ["Fermetures Événementielles • ", "Fermetures pour travaux • ", "Re: "]:
        if title.startswith(prefix):
            title = title[len(prefix):]
    return title

# Fonction pour créer un fil de discussion sur Discord et envoyer un message
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

    # Envoi de la requête POST pour créer le fil de discussion et envoyer le message
    response = requests.post(discord_url, headers=headers, data=json.dumps(payload))

    # Gestion de la réponse de la requête
    if response.status_code == 201:
        # Si la requête a réussi, on ajoute le fil de discussion à la base de données
        print(f"{datetime.now()}: Thread créé avec succès et message envoyé. Titre du post: {thread_title}. Lien du post: {link}")
        thread_id = response.json()['id']
        threads_db[thread_title] = {"thread_id": thread_id, "title": thread_title, "message": thread_content, "replies": [link], "last_update": datetime.now().isoformat()}
        with open('threads.json', 'w') as f:
            json.dump(threads_db, f)
    else:
        # Si la requête a échoué, on affiche un message d'erreur
        print(f"{datetime.now()}: Une erreur est survenue : {response.status_code}, {response.text}. Titre du post: {thread_title}. Lien du post: {link}")

# Fonction pour envoyer un message sur Discord en réponse à un fil de discussion existant
def respond_discord_message(thread_id, message, link, thread_title):
    url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
    payload = {"content": message}
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

    # Envoi de la requête POST pour envoyer le message
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # Gestion de la réponse de la requête
    if response.status_code == 200:
        # Si la requête a réussi, on ajoute le message à la base de données
        print(f"{datetime.now()}: Message envoyé avec succès ! Titre du post: {thread_title}. Lien du post: {link}")
        threads_db[thread_title]['replies'].append(link)
        threads_db[thread_title]['last_update'] = datetime.now().isoformat()
        with open('threads.json', 'w') as f:
            json.dump(threads_db, f)
    else:
        # Si la requête a échoué, on affiche un message d'erreur
        print(f"{datetime.now()}: Erreur lors de l'envoi du message : {response.status_code}, {response.text}. Titre du post: {thread_title}. Lien du post: {link}")

# Boucle infinie pour surveiller les URL RSS et gérer les fils de discussion sur Discord
while True:
    # Si le fichier 'threads.json' existe et n'est pas vide, on charge la base de données des fils de discussion
    if os.path.isfile('threads.json') and os.path.getsize('threads.json') > 0:
        with open('threads.json', 'r') as f:
            threads_db = json.load(f)

    # Pour chaque URL RSS, on parse le flux et on traite chaque entrée
    for rss_url in rss_urls:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[::-1]:  # On traite les entrées de la plus ancienne à la plus récente
            # Récupération des informations de l'entrée
            title = simplify_title(entry.title)
            link = entry.link
            category = entry.category
            content = BeautifulSoup(entry.content[0]['value'], "html.parser").get_text()

            # Préparation du message à envoyer sur Discord
            message = f"Nouveau message sur le forum : \n\n{html.unescape(content)} \n\n Pour répondre à ce message, cliquez sur le lien <{link}>"

            # Récupération du tag id correspondant à la catégorie de l'entrée
            tag_id = get_tag_id_from_category(category)

            # Si le titre de l'entrée est déjà dans la base de données
            if title in threads_db:
                # Si le lien de l'entrée n'est pas déjà dans les réponses du fil de discussion
                if link not in threads_db[title]['replies']:
                    # On envoie un message en réponse au fil de discussion existant
                    respond_discord_message(threads_db[title]['thread_id'], message, link, title)
                else:
                    # Sinon, on indique que l'entrée a déjà été traitée
                    print(f"{datetime.now()}: Cette entrée a déjà été traitée. Titre du post: {title}. Lien du post: {link}")
            else:
                # Si le titre de l'entrée n'est pas dans la base de données, on crée un nouveau fil dediscussion sur Discord et on envoie un message
                create_discord_thread_and_message(title, message, link, tag_id)

    # On parcourt la base de données des fils de discussion
    for title, thread_data in list(threads_db.items()):
        # Si le fil de discussion a une date de dernière mise à jour
        if 'last_update' in thread_data:
            # On convertit la date de dernière mise à jour en objet datetime
            last_update = dateutil.parser.parse(thread_data['last_update'])
            # Si la date de dernière mise à jour est antérieure à 21 jours
            if (datetime.now() - last_update).days > 21: 
                # On supprime le fil de discussion de la base de données
                print(f"{datetime.now()}: Suppression de l'entrée '{title}' du fichier de données car elle n'a pas été mise à jour depuis plus de 3 semaines.")
                del threads_db[title]
                # On sauvegarde la base de données des fils de discussion
                with open('threads.json', 'w') as f:
                    json.dump(threads_db, f)

    # On attend 5min avant de recommencer la boucle
    time.sleep(300)
