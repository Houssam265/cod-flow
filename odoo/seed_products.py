#!/usr/bin/env python3
"""
COD-Flow - Création des produits de démo et initialisation des stocks (Odoo 18)
Compatibilité Odoo 18 : type = 'consu' et is_storable = True.
Initialisation du stock physique dans l'entrepôt principal via stock.quant.
Domaines conformes : conditions en triplets [champ, operateur, valeur], enveloppés dans [domain].
"""

import sys
from odoo_client import odoo

PRODUITS_DEMO = [
    {
        "default_code": "COD-ARGAN-01",
        "name": "Huile d'Argan Pure Bio 100ml",
        "list_price": 150.0,
        "standard_price": 60.0,
        "initial_stock": 50.0,
        "description_sale": "Huile d'argan cosmétique vierge extraite à froid, certifiée bio."
    },
    {
        "default_code": "COD-SAVON-02",
        "name": "Savon Noir Traditionnel à l'Eucalyptus 250g",
        "list_price": 45.0,
        "standard_price": 15.0,
        "initial_stock": 80.0,
        "description_sale": "Savon noir naturel marocain aux huiles essentielles d'eucalyptus."
    },
    {
        "default_code": "COD-PACK-03",
        "name": "Pack Hammam Royal (Savon + Gant Kessa + Argile Ghassoul)",
        "list_price": 120.0,
        "standard_price": 45.0,
        "initial_stock": 30.0,
        "description_sale": "Ensemble complet rituel hammam traditionnel marocain."
    },
    {
        "default_code": "COD-SAFRAN-04",
        "name": "Safran Pur de Taliouine (1g)",
        "list_price": 70.0,
        "standard_price": 35.0,
        "initial_stock": 25.0,
        "description_sale": "Pistils de safran pur terroir de Taliouine AOP."
    },
    {
        "default_code": "COD-SERUM-05",
        "name": "Sérum Anti-Âge Figue de Barbarie 30ml",
        "list_price": 220.0,
        "standard_price": 90.0,
        "initial_stock": 5.0,  # Stock bas intentionnel pour déclencher la règle de réapprovisionnement
        "description_sale": "Élixir précieux anti-rides à base d'huile de pépins de figue de barbarie."
    }
]


def adjust_stock(product_product_id, location_id, qty):
    """
    Initialise ou ajuste la quantité en stock pour un produit donné dans un emplacement interne.
    Gère l'inventaire via inventory_quantity + action_apply_inventory (norme Odoo 16/17/18).
    L'appel action_apply_inventory applique l'inventaire en base mais renvoie None,
    ce qui provoque une Fault XML-RPC 'cannot marshal None' : cette erreur est traitée comme un succès.
    Aucun doublage de stock via quant.quantity n'est effectué.
    """
    try:
        # Recherche d'un quant existant avec domaine conforme
        domain_quant = [
            ["product_id", "=", product_product_id],
            ["location_id", "=", location_id]
        ]
        existing_quants = odoo.execute_kw(
            "stock.quant",
            "search_read",
            [domain_quant],
            {"fields": ["id", "quantity"]}
        )

        # Si le stock est déjà exactement à la quantité souhaitée, aucun ajustement requis
        if existing_quants and float(existing_quants[0].get("quantity", 0.0)) == float(qty):
            return f"Stock déjà conforme : {existing_quants[0]['quantity']} unités"

        # Méthode standard Odoo 16/17/18 : création ou mise à jour de l'inventaire
        if existing_quants:
            quant_id = existing_quants[0]["id"]
            odoo.execute_kw("stock.quant", "write", [[quant_id], {"inventory_quantity": qty}])
        else:
            quant_payload = {
                "product_id": product_product_id,
                "location_id": location_id,
                "inventory_quantity": qty,
            }
            quant_id = odoo.execute_kw("stock.quant", "create", [quant_payload])

        # Application de l'inventaire pour valider le stock physique
        # Note : Odoo applique l'inventaire avec succès mais renvoie None, ce qui provoque
        # une Fault XML-RPC "cannot marshal None". Cette exception est traitée comme un succès.
        try:
            odoo.execute_kw("stock.quant", "action_apply_inventory", [[quant_id]])
        except Exception as apply_err:
            err_str = str(apply_err).lower()
            fault_str = getattr(apply_err, "faultString", "").lower()
            if "cannot marshal none" in err_str or "cannot marshal none" in fault_str:
                pass  # L'inventaire a bien été appliqué côté Odoo
            else:
                return f"[ERREUR] Échec de action_apply_inventory : {apply_err}"

        # Vérification de la quantité réelle (qty_available) sur product.product
        prod_info = odoo.execute_kw(
            "product.product",
            "read",
            [[product_product_id]],
            {"fields": ["qty_available"]}
        )
        real_qty = prod_info[0].get("qty_available", 0.0) if prod_info else 0.0

        if float(real_qty) == float(qty):
            return f"Stock initialisé et confirmé à {real_qty} u. (attendu: {qty})"
        else:
            return f"Stock appliqué : {real_qty} u. constatées (cible: {qty})"

    except Exception as e:
        return f"[ERREUR] Impossible d'ajuster le stock : {e}"


def seed_products():
    print("=" * 65)
    print("  COD-Flow : Création des produits de démo et stock initial")
    print("             Norme Odoo 18 (type='consu', is_storable=True)")
    print("=" * 65)

    uid, models = odoo.connect()
    if not uid:
        print("[KO] Arrêt du script : Impossible de se connecter à Odoo.")
        sys.exit(1)

    # Récupération de l'emplacement de stock interne
    domain_loc = [["usage", "=", "internal"]]
    internal_loc_ids = odoo.execute_kw(
        "stock.location",
        "search",
        [domain_loc],
        {"limit": 1}
    )
    if not internal_loc_ids:
        print("[KO] Aucun emplacement de stock interne trouvé (usage='internal'). Le module 'stock' est-il configuré ?")
        sys.exit(1)
    location_id = internal_loc_ids[0]

    # Inspection des champs de product.template pour confirmer la présence de is_storable (Odoo 18)
    template_fields = odoo.execute_kw(
        "product.template",
        "fields_get",
        [["type", "is_storable"]]
    )
    has_is_storable = "is_storable" in template_fields

    if has_is_storable:
        print("[INFO] Champ Odoo 18 'is_storable' détecté sur product.template.")
    else:
        print("[INFO] 'is_storable' non présent. Mode de compatibilité Odoo standard activé.")

    crees = 0
    existants = 0

    for item in PRODUITS_DEMO:
        ref = item["default_code"]
        name = item["name"]
        price = item["list_price"]
        cost = item["standard_price"]
        init_qty = item["initial_stock"]
        desc = item["description_sale"]

        try:
            # Recherche idempotente par référence interne
            domain_ref = [["default_code", "=", ref]]
            existing = odoo.execute_kw(
                "product.template",
                "search",
                [domain_ref]
            )

            if existing:
                template_id = existing[0]
                print(f"  [SKIP] Le produit '{ref}' ({name}) existe déjà (ID template: {template_id}).")
                existants += 1
            else:
                product_data = {
                    "name": name,
                    "default_code": ref,
                    "list_price": price,
                    "standard_price": cost,
                    "sale_ok": True,
                    "purchase_ok": True,
                    "description_sale": desc,
                }

                # Odoo 18 unifie les consommables et stockables via is_storable
                if has_is_storable:
                    product_data["type"] = "consu"
                    product_data["is_storable"] = True
                else:
                    product_data["type"] = "product"

                template_id = odoo.execute_kw("product.template", "create", [product_data])
                print(f"  [CRÉÉ] Produit '{ref}' ({name}) créé (ID template: {template_id}, Prix: {price} MAD).")
                crees += 1

            # Récupération de la variante product.product pour initialiser le stock
            domain_variant = [["product_tmpl_id", "=", template_id]]
            prod_ids = odoo.execute_kw(
                "product.product",
                "search",
                [domain_variant],
                {"limit": 1}
            )
            if prod_ids:
                prod_product_id = prod_ids[0]
                status_stock = adjust_stock(prod_product_id, location_id, init_qty)
                print(f"         -> Statut Stock (Variante ID {prod_product_id}) : {status_stock}")

        except Exception as e:
            print(f"  [ERREUR] Impossible de traiter le produit '{ref}' : {e}")

    print("-" * 65)
    print(f"Bilan : {len(PRODUITS_DEMO)} produits traités | {crees} créés | {existants} existants")
    print("=" * 65)


if __name__ == "__main__":
    seed_products()
