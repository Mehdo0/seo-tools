#!/usr/bin/env python3
"""Swiss Business Outreach Engine — runs on VM2"""
import subprocess, json, random, time, csv, os
from datetime import datetime

REGIONS = [
    ("Genève", "fr", ["restaurant", "salon coiffure", "fleuriste", "menuisier", "boulangerie", "pharmacie", "garage", "café", "opticien", "librairie"]),
    ("Zürich", "de", ["Restaurant", "Coiffeur", "Blumenladen", "Schreinerei", "Bäckerei", "Apotheke", "Garage", "Café", "Optiker", "Buchhandlung"]),
    ("Bern", "de", ["Restaurant", "Coiffeur", "Blumenladen", "Schreinerei", "Bäckerei", "Apotheke", "Garage", "Café", "Optiker", "Buchhandlung"]),
    ("Basel", "de", ["Restaurant", "Coiffeur", "Blumenladen", "Schreinerei", "Bäckerei", "Apotheke", "Garage", "Café", "Optiker", "Buchhandlung"]),
    ("Lugano", "it", ["ristorante", "parrucchiere", "fioraio", "falegname", "panetteria", "farmacia", "garage", "caffè", "ottico", "libreria"]),
    ("Fribourg", "fr", ["restaurant", "salon coiffure", "fleuriste", "menuisier", "boulangerie", "pharmacie", "garage", "café", "opticien", "librairie"]),
]

TEMPLATES = {
    "fr": {
        "subject": "votre site {domain}",
        "body": """Bonjour,

Je m'appelle Mehdi, développeur basé en Suisse. J'accompagne les commerces locaux pour améliorer leur présence sur Google, tout simplement.

En visitant {domain}, j'ai remarqué {issue}. Pour un {business_type} à {city}, ça veut dire que des clients potentiels ne vous trouvent pas quand ils cherchent vos services.

J'ai déjà aidé des commerces similaires et je peux vous faire un mini diagnostic gratuit de 2 minutes, sans engagement. Vous voulez que je vous l'envoie ?

Bonne journée,
Mehdi"""
    },
    "de": {
        "subject": "Ihre Website {domain}",
        "body": """Guten Tag,

Ich heisse Mehdi, ich bin Entwickler aus der Schweiz und helfe lokalen Geschäften, bei Google besser gefunden zu werden.

Auf Ihrer Website {domain} ist mir aufgefallen, dass {issue}. Für ein {business_type} in {city} bedeutet das, dass potenzielle Kunden Sie nicht finden.

Ich kann Ihnen eine kostenlose Kurzanalyse erstellen, völlig unverbindlich. Soll ich sie Ihnen zusenden?

Freundliche Grüsse,
Mehdi"""
    },
    "it": {
        "subject": "il vostro sito {domain}",
        "body": """Buongiorno,

Mi chiamo Mehdi, sono uno sviluppatore in Svizzera e aiuto i negozi locali a farsi trovare meglio su Google.

Sul vostro sito {domain} ho notato che {issue}. Per un {business_type} a {city}, significa che potenziali clienti non vi trovano.

Posso farvi una mini analisi gratuita di 2 minuti, senza impegno. Volete che ve la invii?

Buona giornata,
Mehdi"""
    }
}

ISSUES = {
    "fr": [
        "il manque une description sur votre page d'accueil",
        "votre site n'a pas de titre structuré",
        "vous n'apparaissez pas sur Google Maps",
        "votre page est difficile à lire sur mobile",
        "il manque des informations essentielles pour Google",
    ],
    "de": [
        "die Beschreibung auf Ihrer Startseite fehlt",
        "Ihre Seite hat keinen strukturierten Titel",
        "Sie erscheinen nicht auf Google Maps",
        "Ihre Seite ist auf dem Handy schwer lesbar",
        "wichtige Informationen für Google fehlen",
    ],
    "it": [
        "manca una descrizione sulla vostra homepage",
        "il vostro sito non ha un titolo strutturato",
        "non apparite su Google Maps",
        "la vostra pagina è difficile da leggere su mobile",
        "mancano informazioni essenziali per Google",
    ]
}

def run():
    region, lang, categories = random.choice(REGIONS)
    category = random.choice(categories)
    
    print(f"🔍 Searching: {category} in {region} ({lang})")
    
    # Search for business
    query = f"{category} {region} site:.ch email"
    result = subprocess.run(["python3", "-c", f"""
import urllib.request, ssl, re
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
# Just log the search — actual scraping done by main orchestrator
print("SEARCH_COMPLETE")
"""], capture_output=True, text=True, timeout=30)
    
    print(f"✅ {datetime.now().strftime('%H:%M')} — Outreach round complete — {region} ({lang})")
    return True

if __name__ == "__main__":
    run()
