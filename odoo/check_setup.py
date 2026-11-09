#!/usr/bin/env python3
"""
COD-Flow - Vérification globale de la configuration Odoo 18
Contrôle de manière exhaustive et affiche un rapport OK/KO pour :
  1. Champs personnalisés sur sale.order (4 champs)
  2. Produits de démo et quantités en stock (5 produits)
  3. Clients de démo marocains (5 contacts)
  4. Règles de réapprovisionnement / stock minimum (5 règles)
Domaines conformes : conditions en triplets [champ, operateur, valeur], enveloppés dans [domain].
"""

import sys
from odoo_client import odoo

CHAMPS_ATTENDUS = ["x_canal", "x_message_id", "x_statut_livraison", "x_motif_retour"]
REFS_PRODUITS = [
    "COD-ARGAN-01",
    "COD-SAVON-02",
    "COD-PACK-03",
    "COD-SAFRAN-04",
    "COD-SERUM-05"
]
STOCKS_ATTENDUS = {
    "COD-ARGAN-01": 50.0,
    "COD-SAVON-02": 80.0,
    "COD-PACK-03": 30.0,
    "COD-SAFRAN-04": 25.0,
    "COD-SERUM-05": 5.0,
}
CLIENTS_ATTENDUS = [
    "+212661234567",
    "+212662987654",
    "+212670112233",
    "+212663445566",
    "+212671889900"
]


def check_setup():
    print("=" * 70)
    print("          COD-Flow : RAPPORT DE VÉRIFICATION DU SETUP ODOO 18")
    print("=" * 70)

    uid, models = odoo.connect()
    if not uid:
        print("\n[CRITIQUE] Impossible d'établir la connexion avec Odoo.")
        print("Vérifiez vos conteneurs Docker et les identifiants dans .env.")
        sys.exit(1)

    erreurs_totales = 0

    # 1. Vérification des champs personnalisés
    print("\n--- 1. Champs personnalisés sur le modèle 'sale.order' ---")
    domain_model = [["model", "=", "sale.order"]]
    model_ids = odoo.execute_kw("ir.model", "search", [domain_model])
    if not model_ids:
        print("  [KO] Modèle 'sale.order' introuvable !")
        erreurs_totales += len(CHAMPS_ATTENDUS)
    else:
        model_id = model_ids[0]
        domain_fields = [
            ["model_id", "=", model_id],
            ["name", "in", CHAMPS_ATTENDUS]
        ]
        fields_found = odoo.execute_kw(
            "ir.model.fields",
            "search_read",
            [domain_fields],
            {"fields": ["name", "field_description", "ttype"]}
        )
        fields_dict = {f["name"]: f for f in fields_found}

        for nom_champ in CHAMPS_ATTENDUS:
            if nom_champ in fields_dict:
                info = fields_dict[nom_champ]
                print(f"  [OK] Champ '{nom_champ}' présent ({info['field_description']}, type: {info['ttype']})")
            else:
                print(f"  [KO] Champ '{nom_champ}' MANQUANT. Exécutez create_custom_fields.py")
                erreurs_totales += 1

    # 2. Vérification des produits et du stock
    print("\n--- 2. Produits de démo et état du stock ---")
    domain_prods = [["default_code", "in", REFS_PRODUITS]]
    produits_trouves = odoo.execute_kw(
        "product.product",
        "search_read",
        [domain_prods],
        {"fields": ["id", "name", "default_code", "list_price", "qty_available"]}
    )
    prod_dict = {p["default_code"]: p for p in produits_trouves}

    for ref in REFS_PRODUITS:
        if ref in prod_dict:
            prod = prod_dict[ref]
            qty = prod.get("qty_available", 0.0)
            expected_qty = STOCKS_ATTENDUS.get(ref, 0.0)
            if float(qty) == float(expected_qty):
                print(f"  [OK] {ref} : '{prod['name']}' | Prix : {prod['list_price']} MAD | En stock : {qty} u. (conforme)")
            else:
                print(f"  [KO] {ref} : '{prod['name']}' | Stock incorrect : {qty} u. (attendu: {expected_qty} u.). Exécutez seed_products.py")
                erreurs_totales += 1
        else:
            print(f"  [KO] Produit '{ref}' MANQUANT. Exécutez seed_products.py")
            erreurs_totales += 1

    # 3. Vérification des clients de démo
    print("\n--- 3. Clients de démo (format +212) ---")
    domain_clients = [
        "|",
        ["phone", "in", CLIENTS_ATTENDUS],
        ["mobile", "in", CLIENTS_ATTENDUS]
    ]
    clients_trouves = odoo.execute_kw(
        "res.partner",
        "search_read",
        [domain_clients],
        {"fields": ["name", "phone", "mobile", "city"]}
    )
    phones_trouves = set()
    for c in clients_trouves:
        if c.get("phone"):
            phones_trouves.add(c["phone"])
        if c.get("mobile"):
            phones_trouves.add(c["mobile"])

    for tel in CLIENTS_ATTENDUS:
        if tel in phones_trouves:
            client = next(c for c in clients_trouves if c.get("phone") == tel or c.get("mobile") == tel)
            print(f"  [OK] Client trouvé : {client['name']} ({client.get('city') or 'Sans ville'}) | {tel}")
        else:
            print(f"  [KO] Client avec téléphone '{tel}' MANQUANT. Exécutez seed_customers.py")
            erreurs_totales += 1

    # 4. Vérification des règles de réapprovisionnement
    print("\n--- 4. Règles de stock minimum (Orderpoints) ---")
    orderpoints = odoo.execute_kw(
        "stock.warehouse.orderpoint",
        "search_read",
        [[]],
        {"fields": ["product_id", "product_min_qty", "product_max_qty"]}
    )
    orderpoint_prod_ids = {op["product_id"][0]: op for op in orderpoints if op.get("product_id")}

    for ref in REFS_PRODUITS:
        if ref in prod_dict:
            prod_id = prod_dict[ref]["id"]
            if prod_id in orderpoint_prod_ids:
                op = orderpoint_prod_ids[prod_id]
                print(f"  [OK] Règle configurée pour {ref} : Min={op['product_min_qty']} / Max={op['product_max_qty']}")
            else:
                print(f"  [KO] Aucune règle pour {ref}. Exécutez seed_orderpoints.py")
                erreurs_totales += 1

    # Résumé
    print("\n" + "=" * 70)
    if erreurs_totales == 0:
        print("  RÉSULTAT GLOBAL : [SUCCÈS] Tous les éléments Odoo 18 sont en place !")
        print("  La plateforme est prête pour l'orchestration Make.com et les tests.")
    else:
        print(f"  RÉSULTAT GLOBAL : [ATTENTION] {erreurs_totales} élément(s) non conforme(s).")
        print("  Veuillez lancer les scripts manquants correspondants.")
    print("=" * 70)


if __name__ == "__main__":
    check_setup()
