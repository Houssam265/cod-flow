#!/usr/bin/env python3
"""
COD-Flow - Simulateur d'envoi de messages vers le Webhook Make.com (S1)
Lit les messages de test dans llm/messages_test.json, les envoie au Webhook Make (S1)
et journalise les temps de réponse, codes HTTP et retours d'exécution.
Bibliothèque standard uniquement (urllib.request, json, time).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def load_env():
    """Charge le fichier .env sans dépendance tierce."""
    candidates = [
        Path.cwd() / ".env",
        Path.cwd() / "odoo" / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent / "odoo" / ".env",
        Path(__file__).resolve().parent.parent / "odoo" / ".env.example",
    ]
    for p in candidates:
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
            return p
    return None


def run_simulator():
    parser = argparse.ArgumentParser(description="Simulateur d'envoi de commandes COD-Flow")
    parser.add_argument("--id", type=str, help="Identifiant du message spécifique à envoyer (ex: MSG-01)")
    parser.add_argument("--count", type=int, default=None, help="Nombre de messages à envoyer (ex: 5)")
    parser.add_argument("--delay", type=float, default=2.0, help="Délai en secondes entre deux envois (défaut: 2.0s)")
    parser.add_argument("--dry-run", action="store_true", help="Simule l'envoi sans appeler réellement le webhook Make")
    args = parser.parse_args()

    env_path = load_env()
    webhook_url = os.environ.get("MAKE_WEBHOOK_URL_S1") or os.environ.get("MAKE_WEBHOOK_URL")

    print("=" * 70)
    print("      COD-Flow : SIMULATEUR D'ENVOI DE MESSAGES (MAKE WEBHOOK)")
    print("=" * 70)
    print(f"Fichier d'environnement : {env_path or 'Variables système'}")
    print(f"URL Webhook Make (S1)  : {webhook_url or 'NON DÉFINIE'}")
    print(f"Mode simulation (Dry)   : {'OUI' if args.dry_run else 'NON'}")
    print("-" * 70)

    # Chargement des messages de test
    test_file = Path(__file__).resolve().parent.parent / "llm" / "messages_test.json"
    if not test_file.is_file():
        print(f"[ERREUR] Fichier de messages introuvable : {test_file}")
        sys.exit(1)

    with open(test_file, "r", encoding="utf-8") as f:
        messages = json.load(f)

    # Filtrage selon arguments
    if args.id:
        messages = [m for m in messages if m.get("id") == args.id]
        if not messages:
            print(f"[ERREUR] Aucun message trouvé avec l'identifiant '{args.id}'.")
            sys.exit(1)
    elif args.count:
        messages = messages[:args.count]

    # Fichier de journalisation des résultats
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"simulator_run_{timestamp_str}.jsonl"

    print(f"Nombre de messages à injecter : {len(messages)}")
    print(f"Fichier de journalisation : {log_file}")
    print("-" * 70)

    reussites = 0
    erreurs = 0

    with open(log_file, "w", encoding="utf-8") as log_out:
        for idx, item in enumerate(messages, start=1):
            msg_id = item.get("id")
            category = item.get("categorie")
            text = item.get("message")

            # Construction du payload simulant un événement entrant Telegram/WhatsApp
            payload = {
                "source": "simulator",
                "x_message_id": f"TEST-{msg_id}-{int(time.time())}",
                "canal": "telegram",
                "sender": {
                    "id": f"tg_user_{idx:03d}",
                    "username": f"client_{msg_id.lower().replace('-', '_')}",
                    "first_name": "Testeur",
                },
                "raw_text": text,
                "sent_at": datetime.now().isoformat(),
            }

            print(f"[{idx}/{len(messages)}] Envoi de {msg_id} ({category})...")
            start_time = time.time()

            result_entry = {
                "message_id": msg_id,
                "categorie": category,
                "payload_sent": payload,
                "sent_at": datetime.now().isoformat(),
            }

            if args.dry_run or not webhook_url or "votre_token" in webhook_url:
                duration_ms = 0.0
                result_entry["status_code"] = 200 if args.dry_run else 0
                result_entry["response_body"] = "[DRY-RUN / URL NON CONFIGURÉE] Payload validé localement."
                result_entry["duration_ms"] = duration_ms
                print(f"  -> [DRY-RUN] Message validé (Simulation). Webhook Make non sollicité.")
                reussites += 1
            else:
                try:
                    data_bytes = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        webhook_url,
                        data=data_bytes,
                        headers={"Content-Type": "application/json", "User-Agent": "COD-Flow-Simulator/1.0"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        duration_ms = round((time.time() - start_time) * 1000, 2)
                        resp_body = resp.read().decode("utf-8", errors="replace")
                        status_code = resp.status

                        result_entry["status_code"] = status_code
                        result_entry["response_body"] = resp_body
                        result_entry["duration_ms"] = duration_ms

                        print(f"  -> [OK] HTTP {status_code} ({duration_ms} ms) | Réponse : {resp_body[:60]}")
                        reussites += 1

                except urllib.error.HTTPError as http_err:
                    duration_ms = round((time.time() - start_time) * 1000, 2)
                    err_body = http_err.read().decode("utf-8", errors="replace")
                    result_entry["status_code"] = http_err.code
                    result_entry["error"] = str(http_err)
                    result_entry["response_body"] = err_body
                    result_entry["duration_ms"] = duration_ms
                    print(f"  -> [ERREUR HTTP {http_err.code}] {err_body[:80]}")
                    erreurs += 1

                except Exception as ex:
                    duration_ms = round((time.time() - start_time) * 1000, 2)
                    result_entry["status_code"] = 0
                    result_entry["error"] = str(ex)
                    result_entry["duration_ms"] = duration_ms
                    print(f"  -> [ÉCHEC ENVOI] {ex}")
                    erreurs += 1

            # Écriture dans le journal JSON Lines
            log_out.write(json.dumps(result_entry, ensure_ascii=False) + "\n")
            log_out.flush()

            if idx < len(messages) and not args.dry_run:
                time.sleep(args.delay)

    print("-" * 70)
    print(f"Bilan simulation : {len(messages)} traités | {reussites} succès | {erreurs} échecs")
    print(f"Journal complet disponible dans : {log_file}")
    print("=" * 70)


if __name__ == "__main__":
    run_simulator()

