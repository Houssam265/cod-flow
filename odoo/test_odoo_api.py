#!/usr/bin/env python3
"""
COD-Flow - Test de connexion API XML-RPC Odoo 18
Vérifie la disponibilité d'Odoo, l'authentification et l'état des modules requis (sale, stock, account).
Domaines conformes à la syntaxe canonique Odoo : conditions en triplets, domaine en liste de triplets.
"""

import sys
from odoo_client import odoo


def test_api():
    print("=" * 60)
    print("  COD-Flow : Test de connexion API XML-RPC Odoo 18")
    print("=" * 60)
    print(f"Fichier de configuration détecté : {odoo.env_loaded or 'Variables système'}")
    print(f"URL cible : {odoo.url}")
    print(f"Base de données : {odoo.db}")
    print(f"Utilisateur : {odoo.user}")
    print("-" * 60)

    uid, models = odoo.connect()
    if not uid:
        print("\n[KO] La connexion a échoué. Corrigez les paramètres dans .env avant de continuer.")
        sys.exit(1)

    print(f"[OK] Authentification réussie ! Identifiant utilisateur (UID) : {uid}")

    # Vérification de la version du serveur
    try:
        version_info = odoo._common.version()
        server_version = version_info.get("server_version", "Inconnue")
        server_serie = version_info.get("server_serie", "Inconnue")
        protocol_version = version_info.get("protocol_version", "Inconnu")
        print(f"[OK] Serveur Odoo détecté : v{server_version} (Série {server_serie}, Protocole {protocol_version})")
    except Exception as e:
        print(f"[AVERTISSEMENT] Impossible de lire les détails de version : {e}")

    # Vérification des modules installés
    print("-" * 60)
    print("Vérification des modules métier indispensables pour COD-Flow :")
    modules_requis = {
        "sale": "Gestion des Ventes (sale.order)",
        "stock": "Gestion des Stocks (stock.picking, stock.quant)",
        "account": "Facturation & Comptabilité (account.move, account.payment)"
    }

    tous_installes = True
    for mod_name, mod_label in modules_requis.items():
        try:
            # Domaine Odoo conforme :
            # 1. Chaque condition est un triplet (champ, opérateur, valeur)
            # 2. Le domaine est une liste de triplets : [['name', '=', mod_name], ['state', '=', 'installed']]
            # 3. Enveloppé dans la liste d'arguments positionnels pour execute_kw : [[domain]]
            domain = [
                ["name", "=", mod_name],
                ["state", "=", "installed"]
            ]
            ids = odoo.execute_kw(
                "ir.module.module",
                "search",
                [domain]
            )
            if ids:
                print(f"  [OK] Module '{mod_name}' ({mod_label}) : Installé")
            else:
                print(f"  [KO] Module '{mod_name}' ({mod_label}) : NON installé")
                tous_installes = False
        except Exception as e:
            print(f"  [KO] Erreur lors de la vérification du module '{mod_name}' : {e}")
            tous_installes = False

    print("=" * 60)
    if tous_installes:
        print("RÉSULTAT : Odoo est opérationnel et prêt pour les scripts de configuration !")
    else:
        print("ATTENTION : Certains modules Odoo nécessaires ne sont pas encore installés.")
        print("            Connectez-vous à l'interface Odoo (Apps) et installez 'Ventes', 'Inventaire' et 'Facturation'.")
    print("=" * 60)


if __name__ == "__main__":
    test_api()
