# ============================================================
# 🏀 AGENT IA NBA — OVER/UNDER TOTAL POINTS
# ============================================================
# Source données : Balldontlie (gratuit, sans clé)
# Envoi automatique via GitHub Actions à 15h00 (Lomé)
# ============================================================

import requests
import time
import os
from datetime import date

# ============================================================
# ⚙️ CONFIGURATION
# ============================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")

BASE_URL = "https://api.balldontlie.io/v1"
SAISON   = 2024  # saison NBA 2024-25

# ============================================================
# 🎯 SEUILS DE FILTRAGE NBA
# ============================================================

FILTER = {
    "total_avg_min": 215.0,      # Total points moyen combiné minimum
    "over220_pct_min": 45.0,     # % de matchs avec plus de 220 pts minimum
    "pts_scored_min": 108.0,     # Une équipe doit marquer au moins 108 pts en moy.
}


# ============================================================
# 📲 TELEGRAM
# ============================================================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for i in range(0, len(message), 4096):
        try:
            requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": message[i:i+4096]
            }, timeout=10)
        except Exception as e:
            print(f"⚠️ Erreur Telegram : {e}")


# ============================================================
# 📡 API BALLDONTLIE
# ============================================================

def get_games_today():
    """Récupère les matchs NBA du jour"""
    today = date.today().strftime("%Y-%m-%d")
    try:
        resp = requests.get(f"{BASE_URL}/games", params={
            "dates[]": today,
            "per_page": 30
        }, timeout=10)
        data = resp.json().get("data", [])
        print(f"📅 {len(data)} match(s) NBA trouvé(s) aujourd'hui")
        return data
    except Exception as e:
        print(f"⚠️ Erreur récupération matchs : {e}")
        return []


def get_team_stats(team_id, num_games=20):
    """
    Calcule les stats moyennes d'une équipe
    sur ses N derniers matchs de la saison.
    """
    try:
        resp = requests.get(f"{BASE_URL}/games", params={
            "team_ids[]": team_id,
            "seasons[]": SAISON,
            "per_page": num_games
        }, timeout=10)
        games = resp.json().get("data", [])
        time.sleep(0.4)

        pts_scored  = []
        pts_allowed = []
        totals      = []

        for g in games:
            home_score = g.get("home_team_score") or 0
            away_score = g.get("visitor_team_score") or 0

            # Ignorer les matchs pas encore joués
            if home_score == 0 and away_score == 0:
                continue

            if g["home_team"]["id"] == team_id:
                scored  = home_score
                allowed = away_score
            else:
                scored  = away_score
                allowed = home_score

            pts_scored.append(scored)
            pts_allowed.append(allowed)
            totals.append(scored + allowed)

        if not pts_scored:
            return None

        n = len(totals)
        return {
            "avg_scored":   round(sum(pts_scored)  / n, 1),
            "avg_allowed":  round(sum(pts_allowed) / n, 1),
            "avg_total":    round(sum(totals)       / n, 1),
            "games":        n,
            "over220_pct":  round(sum(1 for t in totals if t > 220) / n * 100, 1),
            "over215_pct":  round(sum(1 for t in totals if t > 215) / n * 100, 1),
            "over210_pct":  round(sum(1 for t in totals if t > 210) / n * 100, 1),
            "max_pts":      max(totals),
            "min_pts":      min(totals),
        }

    except Exception as e:
        print(f"⚠️ Erreur stats équipe {team_id} : {e}")
        return None


# ============================================================
# 🔍 FILTRE
# ============================================================

def passes_filter(home_stats, away_stats):
    """Retourne True si le match est intéressant pour Over/Under"""
    if not home_stats or not away_stats:
        return False

    score = 0

    # Check 1 : Total moyen combiné
    combined = (home_stats["avg_total"] + away_stats["avg_total"]) / 2
    if combined >= FILTER["total_avg_min"]:
        score += 1

    # Check 2 : % Over 220 combiné
    avg_over220 = (home_stats["over220_pct"] + away_stats["over220_pct"]) / 2
    if avg_over220 >= FILTER["over220_pct_min"]:
        score += 1

    # Check 3 : Au moins une équipe attaque fort
    if max(home_stats["avg_scored"], away_stats["avg_scored"]) >= FILTER["pts_scored_min"]:
        score += 1

    return score >= 2


# ============================================================
# 📋 TEMPLATE
# ============================================================

def build_template(match_info, home_stats, away_stats):
    combined_avg = round((home_stats["avg_total"] + away_stats["avg_total"]) / 2, 1)
    expected_total = round(
        (home_stats["avg_scored"] + away_stats["avg_scored"] +
         home_stats["avg_allowed"] + away_stats["avg_allowed"]) / 2, 1
    )

    return f"""
========================================
Match NBA : {match_info['home']} vs {match_info['away']}
Date      : {match_info['date']} | Heure locale : {match_info['time']} ET
========================================
{match_info['home']} (Domicile) :
- Pts marqués / match (moy.)   : {home_stats['avg_scored']}
- Pts encaissés / match (moy.) : {home_stats['avg_allowed']}
- Total pts / match (moy.)     : {home_stats['avg_total']}
- Over 220 pts                 : {home_stats['over220_pct']}% des matchs
- Over 215 pts                 : {home_stats['over215_pct']}% des matchs
- Over 210 pts                 : {home_stats['over210_pct']}% des matchs
- Min / Max total              : {home_stats['min_pts']} / {home_stats['max_pts']}

{match_info['away']} (Extérieur) :
- Pts marqués / match (moy.)   : {away_stats['avg_scored']}
- Pts encaissés / match (moy.) : {away_stats['avg_allowed']}
- Total pts / match (moy.)     : {away_stats['avg_total']}
- Over 220 pts                 : {away_stats['over220_pct']}% des matchs
- Over 215 pts                 : {away_stats['over215_pct']}% des matchs
- Over 210 pts                 : {away_stats['over210_pct']}% des matchs
- Min / Max total              : {away_stats['min_pts']} / {away_stats['max_pts']}

Synthèse :
- Total moyen combiné          : {combined_avg} pts
- Total attendu estimé         : {expected_total} pts
- Matchs analysés ({match_info['home']}) : {home_stats['games']}
- Matchs analysés ({match_info['away']}) : {away_stats['games']}
========================================"""


# ============================================================
# 🚀 ANALYSE PRINCIPALE
# ============================================================

def lancer_analyse():
    today  = date.today().strftime("%Y-%m-%d")
    games  = get_games_today()

    if not games:
        send_telegram("🏀 Aucun match NBA aujourd'hui.")
        return

    send_telegram(f"🏀 NBA — Analyse du {today}\n📊 {len(games)} match(s) en cours d'analyse...")

    retenus = []

    for game in games:
        home_team = game["home_team"]
        away_team = game["visitor_team"]
        game_time = game.get("status", "N/A")

        print(f"\n📊 {away_team['full_name']} @ {home_team['full_name']}")

        home_stats = get_team_stats(home_team["id"])
        away_stats = get_team_stats(away_team["id"])

        if passes_filter(home_stats, away_stats):
            print(f"   ✅ RETENU")
            match_info = {
                "home":  home_team["full_name"],
                "away":  away_team["full_name"],
                "date":  today,
                "time":  game_time
            }
            retenus.append(build_template(match_info, home_stats, away_stats))
        else:
            print(f"   ❌ REJETÉ")

    if retenus:
        send_telegram(f"✅ {len(retenus)} match(s) NBA retenu(s) aujourd'hui :")
        for t in retenus:
            send_telegram(t)
        send_telegram(
            "📎 Analyse ces matchs NBA pour Over/Under.\n"
            "Pour chaque match :\n"
            "1. Ligne Over/Under recommandée (210 / 215 / 220 / 225)\n"
            "2. Probabilité Over + confiance (Fort / Moyen / Faible)\n"
            "3. Probabilité Under + confiance\n"
            "4. Points forts et risques\n"
            "5. Ta recommandation finale"
        )
    else:
        send_telegram("⚠️ Aucun match NBA ne passe les filtres aujourd'hui.")

    print(f"\n✅ Terminé — {len(retenus)} match(s) retenu(s)")


# ============================================================
# ▶️ LANCEMENT
# ============================================================

if __name__ == "__main__":
    lancer_analyse()
