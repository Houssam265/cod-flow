#!/usr/bin/env python3
"""
COD-Flow - Création des clients de démo marocains (Odoo 18)
Crée de façon idempotente 5 clients réalistes avec téléphone normalisé +212.
Domaines conformes : conditions en triplets [champ, operateur, valeur], enveloppés dans [domain].
"""

import sys
from odoo_client import odoo

CLIENTS_DEMO = [
    {
        "name": "Youssef El Amrani",
        "phone": "+212661234567",
        "street": "12 Rue Ibn Batouta, Maarif",
        "city": "Casablanca",
        "email": "youssef.amrani@example.ma",
        "comment": "Client régulier - Préfère la livraison l'après-midi."
    },
    {
        "name": "Fatima Zahra Bennani",
        "phone": "+212662987654",
        "street": "45 Avenue Allal Ben Abdellah, Agdal",
        "city": "Rabat",
        "email": "fz.bennani@example.ma",
        "comment": "Livraison à domicile - Appeler avant le passage."
    },
    {
        "name": "Mehdi Chraibi",
        "phone": "+212670112233",
        "street": "8 Derb Dabachi, Médina",
        "city": "Marrakech",
        "email": "mehdi.chraibi@example.ma",
        "comment": "Accès médina : point de rencontre Bab Agnaou."
    },
    {
        "name": "Salma Tazi",
        "phone": "+212663445566",
        "street": "18 Boulevard Hassan II, Ville Nouvelle",
        "city": "Fès",
        "email": "salma.tazi@example.ma",
        "comment": "Commande souvent des packs traditionnels."
    },
    {
        "name": "Karim Berrada",
        "phone": "+212671889900",
        "street": "24 Avenue Mohammed V, Malabata",
        "city": "Tanger",
        "email": "karim.berrada@example.ma",
        "comment": "Disponible au bureau de 9h à 18h."
    }
]


def seed_customers():
    print("=" * 65)
    print("  COD-Flow : Création idempotente des clients de démo")
    print("             Format téléphonique normalisé : +212 (Maroc)")
    print("=" * 65)

    uid, models = odoo.connect()
    if not uid:
        print("[KO] Arrêt du script : Impossible de se connecter à Odoo.")
        sys.exit(1)

    # Récupération de l'identifiant du pays Maroc (MA) avec domaine conforme
    domain_country = [["code", "=", "MA"]]
    maroc_ids = odoo.execute_kw(
        "res.country",
        "search",
        [domain_country],
        {"limit": 1}
    )
    country_id = maroc_ids[0] if maroc_ids else False

    crees = 0
    existants = 0

    for client in CLIENTS_DEMO:
        name = client["name"]
        phone = client["phone"]
        city = client["city"]
        street = client["street"]
        email = client["email"]
        comment = client["comment"]

        try:
            # Recherche idempotente par téléphone ou mobile (opérateur '|' préfixe)
            domain_partner = [
                "|",
                ["phone", "=", phone],
                ["mobile", "=", phone]
            ]
            existing = odoo.execute_kw(
                "res.partner",
                "search",
                [domain_partner]
            )

            if existing:
                partner_id = existing[0]
                print(f"  [SKIP] Client '{name}' déjà existant avec le numéro {phone} (ID: {partner_id}).")
                existants += 1
            else:
                partner_data = {
                    "name": name,
                    "phone": phone,
                    "mobile": phone,
                    "street": street,
                    "city": city,
                    "email": email,
                    "comment": comment,
                    "customer_rank": 1,
                    "is_company": False,
                }
                if country_id:
                    partner_data["country_id"] = country_id

                partner_id = odoo.execute_kw("res.partner", "create", [partner_data])
                print(f"  [CRÉÉ] Client '{name}' ({city}, {phone}) créé avec succès (ID: {partner_id}).")
                crees += 1

        except Exception as e:
            print(f"  [ERREUR] Impossible de traiter le client '{name}' : {e}")

    print("-" * 65)
    print(f"Bilan : {len(CLIENTS_DEMO)} clients vérifiés | {crees} créés | {existants} déjà existants")
    print("=" * 65)


if __name__ == "__main__":
    seed_customers()
