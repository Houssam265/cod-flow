"""
COD-Flow - Module d'aide pour la connexion XML-RPC Odoo 18
Ce script lit la configuration dans .env (sans dépendance externe)
et fournit un client prêt à l'emploi avec gestion d'erreurs en français.
Conforme à la syntaxe execute_kw native d'Odoo pour les domaines de recherche.
"""

import os
import sys
import xmlrpc.client
from pathlib import Path


def load_env_file():
    """Charge les variables du fichier .env le plus proche sans dépendance externe."""
    candidates = [
        Path.cwd() / ".env",
        Path.cwd() / "odoo" / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent / ".env.example",
    ]
    for env_path in candidates:
        if env_path.is_file():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
            return env_path
    return None


class OdooConnection:
    """Gestionnaire de connexion XML-RPC pour Odoo 18."""

    def __init__(self):
        self.env_loaded = load_env_file()
        self.url = os.environ.get("ODOO_URL", "http://localhost:8069").rstrip("/")
        self.db = os.environ.get("ODOO_DB", "codflow_db")
        self.user = os.environ.get("ODOO_USER", "admin@codflow.ma")
        self.password = os.environ.get("ODOO_PASSWORD", "odoo_codflow_password_change_me")
        self.uid = None
        self._common = None
        self._models = None

    def connect(self):
        """Authentifie l'utilisateur sur Odoo et retourne (uid, models)."""
        try:
            self._common = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/common",
                allow_none=True
            )
            # Test d'accès serveur
            version_info = self._common.version()
            odoo_version = version_info.get("server_serie", "Inconnue")
        except ConnectionRefusedError:
            print(f"[ERREUR] Impossible de joindre Odoo sur {self.url}.")
            print("         Vérifiez que le conteneur Docker Odoo est bien démarré (docker compose up -d).")
            return None, None
        except Exception as e:
            print(f"[ERREUR] Erreur de communication avec le serveur Odoo ({self.url}) : {e}")
            return None, None

        try:
            self.uid = self._common.authenticate(self.db, self.user, self.password, {})
            if not self.uid:
                print(f"[ERREUR] Échec d'authentification sur la base '{self.db}'.")
                print(f"         Utilisateur : {self.user}")
                print("         Veuillez vérifier ODOO_USER et ODOO_PASSWORD dans votre fichier .env.")
                return None, None
        except Exception as e:
            print(f"[ERREUR] Exception lors de l'authentification XML-RPC : {e}")
            return None, None

        self._models = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object",
            allow_none=True
        )
        return self.uid, self._models

    @staticmethod
    def _clean_domain(domain):
        """
        Normalise un domaine Odoo pour s'assurer que :
        - Les conditions sont des triplets [champ, operateur, valeur].
        - Les opérateurs préfixes ('|', '&', '!') sont préservés.
        - Aucun sur-empaquetage de listes n'est présent.
        """
        if not domain:
            return []

        if isinstance(domain, tuple):
            domain = list(domain)

        if not isinstance(domain, list):
            return domain

        # Si le domaine a été enveloppé par erreur dans une liste externe (ex: [[[...]]])
        while len(domain) == 1 and isinstance(domain[0], (list, tuple)):
            first = domain[0]
            if len(first) == 0:
                domain = []
                break
            # Cas 1 : le seul élément commence par un opérateur logique ('|', '&', '!')
            # ex: [ ['|', c1, c2] ] -> l'enveloppe externe est superflue
            if isinstance(first[0], str) and first[0] in ("|", "&", "!"):
                domain = list(first)
                continue
            # Cas 2 : le seul élément est déjà un triplet valide [champ, operateur, valeur]
            # ex: [ ['name', '=', 'sale'] ] -> c'est un domaine valide à 1 condition
            if len(first) == 3 and isinstance(first[0], str) and isinstance(first[1], str):
                break
            # Cas 3 : le premier élément est lui-même une liste/tuple (ex: [ [c1, c2] ])
            if isinstance(first[0], (list, tuple)):
                domain = list(first)
                continue
            # Cas 4 : longueur != 3, ce n'est pas un triplet valide
            if len(first) != 3:
                domain = list(first)
                continue
            break

        cleaned = []
        for item in domain:
            if isinstance(item, str) and item in ("|", "&", "!"):
                cleaned.append(item)
            elif isinstance(item, (list, tuple)) and len(item) == 3:
                cleaned.append([item[0], item[1], item[2]])
            else:
                cleaned.append(item)
        return cleaned

    def execute_kw(self, model, method, args=None, kwargs=None):
        """
        Appel natif execute_kw conforme à l'API Odoo :
        models.execute_kw(db, uid, password, model, method, args, kwargs)
        args   : liste des arguments positionnels (ex: [domain])
        kwargs : dictionnaire des arguments nommés (ex: {'fields': ['name']})
        """
        if not self.uid or not self._models:
            uid, models = self.connect()
            if not uid:
                raise RuntimeError("Non connecté à Odoo. Impossible d'exécuter l'appel XML-RPC.")
        if args is None:
            args = []
        else:
            args = list(args)
        if kwargs is None:
            kwargs = {}
        else:
            kwargs = dict(kwargs)

        # Sécurisation défensive pour les méthodes de recherche (search, search_read, search_count)
        if method in ("search", "search_read", "search_count") and args:
            args[0] = self._clean_domain(args[0])

        try:
            return self._models.execute_kw(
                self.db,
                self.uid,
                self.password,
                model,
                method,
                args,
                kwargs
            )
        except xmlrpc.client.Fault as err:
            # Traiter "cannot marshal None" comme un retour None valide (méthodes Odoo renvoyant void/None)
            if "cannot marshal none" in err.faultString.lower():
                return None
            print(f"[ERREUR XML-RPC] Modèle '{model}', Méthode '{method}' : {err.faultString}")
            raise
        except Exception as err:
            print(f"[ERREUR INATTENDUE] Modèle '{model}', Méthode '{method}' : {err}")
            raise

    def search(self, model, domain=None, offset=0, limit=None, order=None):
        """Recherche d'identifiants Odoo avec domaine validé en triplets."""
        clean_d = self._clean_domain(domain or [])
        args = [clean_d]
        kwargs = {}
        if offset:
            kwargs["offset"] = offset
        if limit is not None:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return self.execute_kw(model, "search", args, kwargs)

    def search_read(self, model, domain=None, fields=None, offset=0, limit=None, order=None):
        """Recherche et lecture d'enregistrements Odoo avec domaine validé en triplets."""
        clean_d = self._clean_domain(domain or [])
        args = [clean_d]
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
        if offset:
            kwargs["offset"] = offset
        if limit is not None:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return self.execute_kw(model, "search_read", args, kwargs)

    def execute(self, model, method, *args, **kwargs):
        """
        Méthode générique d'exécution.
        Prend en charge la syntaxe avec arguments variables et kwargs.
        Pour les méthodes de recherche (search, search_read, search_count),
        elle sécurise le domaine pour éviter toute erreur de déballage.
        """
        args_list = list(args)

        # Si un premier argument est un dictionnaire d'options kwargs passé positionnellement
        if len(args_list) >= 2 and isinstance(args_list[-1], dict) and not kwargs:
            kwargs = args_list.pop()

        # Si la méthode attend un domaine (search, search_read, search_count)
        if method in ("search", "search_read", "search_count") and args_list:
            raw_domain = args_list[0]
            clean_d = self._clean_domain(raw_domain)
            args_list[0] = clean_d
            # Pour search_read, si le 2ème argument positionnel est la liste des champs
            if method == "search_read" and len(args_list) >= 2 and isinstance(args_list[1], list):
                fields = args_list[1]
                args_list = [clean_d]
                kwargs["fields"] = fields

        return self.execute_kw(model, method, args=args_list, kwargs=kwargs)


# Instance globale réutilisable
odoo = OdooConnection()
