#!/usr/bin/env python3
"""
COD-Flow - Création des champs personnalisés sur sale.order (Odoo 18)
Crée de façon idempotente les champs :
  - x_canal (sélection : WhatsApp, Telegram, Instagram)
  - x_message_id (char, indexé pour recherche anti-doublon)
  - x_statut_livraison (sélection : En attente, Expédié, Livré, Refusé, Injoignable)
  - x_motif_retour (char/texte)
Domaines conformes : conditions en triplets [champ, operateur, valeur], enveloppés dans [domain].
"""

import sys
from odoo_client import odoo


CHAMPS_A_CREER = [
    {
        "name": "x_canal",
        "field_description": "Canal de commande",
        "ttype": "selection",
        "selection": "[('whatsapp', 'WhatsApp'), ('telegram', 'Telegram'), ('instagram', 'Instagram')]",
        "help": "Canal source par lequel le client a passé sa commande."
    },
    {
        "name": "x_message_id",
        "field_description": "ID Message Source",
        "ttype": "char",
        "index": True,
        "help": "Identifiant unique du message reçu (Telegram update_id/message_id ou Twilio MessageSid) pour éviter les doublons."
    },
    {
        "name": "x_statut_livraison",
        "field_description": "Statut Livraison COD",
        "ttype": "selection",
        "selection": "[('en_attente', 'En attente'), ('expedie', 'Expédié'), ('livre', 'Livré'), ('refuse', 'Refusé'), ('injoignable', 'Injoignable')]",
        "help": "Statut de suivi de la livraison assuré par le transporteur COD."
    },
    {
        "name": "x_motif_retour",
        "field_description": "Motif de retour / échec",
        "ttype": "char",
        "help": "Raison invoquée en cas de refus, colis non réclamé ou impossibilité de joindre le destinataire."
    }
]


def create_fields():
    print("=" * 65)
    print("  COD-Flow : Création idempotente des champs personnalisés")
    print("             Modèle cible : sale.order (Commandes de vente)")
    print("=" * 65)

    uid, models = odoo.connect()
    if not uid:
        print("[KO] Arrêt du script : Impossible de se connecter à Odoo.")
        sys.exit(1)

    # Récupération de l'ir.model pour sale.order via execute_kw
    try:
        domain_model = [["model", "=", "sale.order"]]
        model_ids = odoo.execute_kw("ir.model", "search", [domain_model])
        if not model_ids:
            print("[KO] Modèle 'sale.order' introuvable dans Odoo. Assurez-vous que le module 'sale' est bien installé.")
            sys.exit(1)
        model_id = model_ids[0]
        print(f"[INFO] Modèle 'sale.order' identifié (ID: {model_id})")
    except Exception as e:
        print(f"[ERREUR] Échec de la recherche du modèle 'sale.order' : {e}")
        sys.exit(1)

    total = len(CHAMPS_A_CREER)
    crees = 0
    existants = 0

    for champ in CHAMPS_A_CREER:
        nom = champ["name"]
        label = champ["field_description"]
        ttype = champ["ttype"]

        try:
            # Vérification de l'existence préalable du champ avec domaine conforme
            domain_field = [
                ["model_id", "=", model_id],
                ["name", "=", nom]
            ]
            field_ids = odoo.execute_kw("ir.model.fields", "search", [domain_field])

            if field_ids:
                print(f"  [SKIP] Le champ '{nom}' ({label}) existe déjà (ID: {field_ids[0]}).")
                existants += 1
            else:
                payload = {
                    "name": nom,
                    "field_description": label,
                    "model_id": model_id,
                    "ttype": ttype,
                    "state": "manual",
                }
                if "selection" in champ:
                    payload["selection"] = champ["selection"]
                if "index" in champ:
                    payload["index"] = champ["index"]
                if "help" in champ:
                    payload["help"] = champ["help"]

                new_id = odoo.execute_kw("ir.model.fields", "create", [payload])
                print(f"  [CRÉÉ] Champ '{nom}' ({label}, type: {ttype}) créé avec succès (ID: {new_id}).")
                crees += 1

        except Exception as e:
            print(f"  [ERREUR] Impossible de traiter le champ '{nom}' : {e}")

    print("-" * 65)
    print(f"Bilan : {total} champs vérifiés | {crees} créés | {existants} déjà existants")
    print("=" * 65)


if __name__ == "__main__":
    create_fields()
