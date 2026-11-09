#!/usr/bin/env python3
"""
COD-Flow - Création des règles de réapprovisionnement (Stock minimum)
Modèle Odoo : stock.warehouse.orderpoint
Crée de façon idempotente une règle de stock minimum par produit de démo.
Domaines conformes : conditions en triplets [champ, operateur, valeur], enveloppés dans [domain].
"""

import sys
from odoo_client import odoo

REGLES_SEUILS = {
    "COD-ARGAN-01": {"min_qty": 10.0, "max_qty": 50.0},
    "COD-SAVON-02": {"min_qty": 20.0, "max_qty": 100.0},
    "COD-PACK-03": {"min_qty": 5.0, "max_qty": 30.0},
    "COD-SAFRAN-04": {"min_qty": 5.0, "max_qty": 25.0},
    "COD-SERUM-05": {"min_qty": 10.0, "max_qty": 40.0},  # Stock initial = 5 -> déclenchera un réapprovisionnement
}


def seed_orderpoints():
    print("=" * 65)
    print("  COD-Flow : Création idempotente des règles de réapprovisionnement")
    print("             Modèle cible : stock.warehouse.orderpoint")
    print("=" * 65)

    uid, models = odoo.connect()
    if not uid:
        print("[KO] Arrêt du script : Impossible de se connecter à Odoo.")
        sys.exit(1)

    # Récupération de l'emplacement interne avec domaine conforme
    domain_loc = [["usage", "=", "internal"]]
    loc_ids = odoo.execute_kw(
        "stock.location",
        "search",
        [domain_loc],
        {"limit": 1}
    )
    if not loc_ids:
        print("[KO] Emplacement interne introuvable. Veuillez vérifier la configuration de l'entrepôt.")
        sys.exit(1)
    location_id = loc_ids[0]

    crees = 0
    existants = 0
    non_trouves = 0

    for ref, seuils in REGLES_SEUILS.items():
        min_q = seuils["min_qty"]
        max_q = seuils["max_qty"]

        try:
            # Recherche du produit product.product correspondant
            domain_prod = [["default_code", "=", ref]]
            prod_ids = odoo.execute_kw(
                "product.product",
                "search",
                [domain_prod],
                {"limit": 1}
            )

            if not prod_ids:
                print(f"  [ATTENTION] Produit avec référence '{ref}' introuvable. Exécutez seed_products.py d'abord.")
                non_trouves += 1
                continue

            product_id = prod_ids[0]

            # Recherche d'une règle existante pour ce produit
            domain_rule = [["product_id", "=", product_id]]
            existing_rules = odoo.execute_kw(
                "stock.warehouse.orderpoint",
                "search",
                [domain_rule]
            )

            if existing_rules:
                rule_id = existing_rules[0]
                rule_data = odoo.execute_kw(
                    "stock.warehouse.orderpoint",
                    "read",
                    [[rule_id]],
                    {"fields": ["product_min_qty", "product_max_qty"]}
                )[0]
                print(f"  [SKIP] Règle existante pour '{ref}' (ID: {rule_id}) | Min: {rule_data.get('product_min_qty')} / Max: {rule_data.get('product_max_qty')}")
                existants += 1
            else:
                rule_payload = {
                    "product_id": product_id,
                    "location_id": location_id,
                    "product_min_qty": min_q,
                    "product_max_qty": max_q,
                    "qty_multiple": 1.0,
                }
                new_rule_id = odoo.execute_kw("stock.warehouse.orderpoint", "create", [rule_payload])
                print(f"  [CRÉÉ] Règle créée pour '{ref}' (ID: {new_rule_id}) | Min: {min_q} / Max: {max_q} unités.")
                crees += 1

        except Exception as e:
            print(f"  [ERREUR] Impossible de créer la règle pour '{ref}' : {e}")

    print("-" * 65)
    print(f"Bilan : {len(REGLES_SEUILS)} règles ciblées | {crees} créées | {existants} existantes | {non_trouves} non trouvés")
    print("=" * 65)


if __name__ == "__main__":
    seed_orderpoints()
