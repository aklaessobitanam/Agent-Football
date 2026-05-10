# ============================================================
# 🏒 AGENT IA NHL — OVER/UNDER TOTAL BUTS
# ============================================================
# Source données : API Officielle NHL (gratuite, sans clé)
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

BASE_URL = "https://api-web.nhle.com/v1"

# ============================================================
# 🎯 SEUILS DE FILTRAGE NHL
# ============================================================

FILTER = {
    "total_avg_min": 5.5,      # Total buts moyen combiné minimum
    "over55_pct_min": 45.0,    # % matchs Over 5.5 minimum
    "goals_scored_min": 2.8,   # Une équipe doit marquer au moins 2.8 buts/match
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
# 📡 API NHL OFFICIELLE
# ============================================================

def get_games_today():
    """Récupère les matchs NHL du jour"""
    today = date.today().strftime("%Y-%m-%d")
    try:
        resp = requests.get(f"{BASE_URL}/schedule/{today}", timeout=10)
        game_week = resp.json().get("gameWeek", [])
        for day in game_week:
            if day.get("date") == today:
                games = day.get("games", [])
                print(f"📅 {len(games)} match(s) NHL trouvé(s) aujourd'hui")
                return games
        return []
    except Exception as e:
        print(f"⚠️ Erreur récupération matchs : {e}")
        return []


def get_all_standings():
    """
    Récupère les stats de toutes les équipes en une seule requête.
    Retourne un dictionnaire {teamAbbrev: stats}
    """
    try:
        resp = requests.get(f"{BASE_URL}/standings/now", timeout=10)
        standings = resp.json().get("standings", [])

        stats_by_abbrev = {}
        for team in standings:
            abbrev = team.get("teamAbbrev", {}).get("default", "")
            gp     = team.get("gamesPlayed", 0)
            if gp == 0:
                continue

            gf = team.get("goalFor", 0)
            ga = team.get("goalAgainst", 0)

            avg_scored  = round(gf / gp, 2)
            avg_allowed = round(ga / gp, 2)
            avg_total   = round((gf + ga) / gp, 2)

            stats_by_abbrev[abbrev] = {
                "avg_scored":  avg_scored,
                "avg_allowed": avg_allowed,
                "avg_total":   avg_total,
                "games":       gp,
                "wins":        team.get("wins", 0),
                "losses":      team.get("losses", 0),
                # Estimation Over 5.5 et Over 6.5 basée sur la moyenne
                "over55_pct":  round(min((avg_total - 4.5) / 3.0, 1.0) * 100, 1),
                "over65_pct":  round(min((avg_total - 5.0) / 3.5, 1.0) * 100, 1),
            }

        print(f"✅ Stats récupérées pour {len(stats_by_abbrev)} équipes NHL")
        return stats_by_abbrev

    except Exception as e:
        print(f"⚠️ Erreur récupération standings : {e}")
        return {}


# ============================================================
# 🔍 FILTRE
# ============================================================

def passes_filter(home_stats, away_stats):
    """Retourne True si le match est intéressant pour Over/Under buts"""
    if not home_stats or not away_stats:
        return False

    score = 0

    # Check 1 : Total buts moyen combiné
    combined = (home_stats["avg_total"] + away_stats["avg_total"]) / 2
    if combined >= FILTER["total_avg_min"]:
        score += 1

    # Check 2 : % Over 5.5 combiné
    avg_over55 = (home_stats["over55_pct"] + away_stats["over55_pct"]) / 2
    if avg_over55 >= FILTER["over55_pct_min"]:
        score += 1

    # Check 3 : Au moins une équipe attaque fort
    if max(home_stats["avg_scored"], away_stats["avg_scored"]) >= FILTER["goals_scored_min"]:
        score += 1

    return score >= 2


# ============================================================
# 📋 TEMPLATE
# ============================================================

def build_template(match_info, home_stats, away_stats):
    combined_avg   = round((home_stats["avg_total"] + away_stats["avg_total"]) / 2, 2)
    expected_total = round(
        (home_stats["avg_scored"] + away_stats["avg_scored"] +
         home_stats["avg_allowed"] + away_stats["avg_allowed"]) / 2, 2
    )

    return f"""
========================================
Match NHL : {match_info['home']} vs {match_info['away']}
Date      : {match_info['date']} | Heure : {match_info['time']} ET
========================================
{match_info['home']} (Domicile) :
- Buts marqués / match (moy.)   : {home_stats['avg_scored']}
- Buts encaissés / match (moy.) : {home_stats['avg_allowed']}
- Total buts / match (moy.)     : {home_stats['avg_total']}
- Over 5.5 buts (estimation)    : {home_stats['over55_pct']}%
- Over 6.5 buts (estimation)    : {home_stats['over65_pct']}%
- Bilan saison                  : {home_stats['wins']}V / {home_stats['losses']}D
- Matchs analysés               : {home_stats['games']}

{match_info['away']} (Extérieur) :
- Buts marqués / match (moy.)   : {away_stats['avg_scored']}
- Buts encaissés / match (moy.) : {away_stats['avg_allowed']}
- Total buts / match (moy.)     : {away_stats['avg_total']}
- Over 5.5 buts (estimation)    : {away_stats['over55_pct']}%
- Over 6.5 buts (estimation)    : {away_stats['over65_pct']}%
- Bilan saison                  : {away_stats['wins']}V / {away_stats['losses']}D
- Matchs analysés               : {away_stats['games']}

Synthèse :
- Total buts moyen combiné      : {combined_avg}
- Total buts attendu estimé     : {expected_total}
========================================"""


# ============================================================
# 🚀 ANALYSE PRINCIPALE
# ============================================================

def lancer_analyse():
    today  = date.today().strftime("%Y-%m-%d")
    games  = get_games_today()

    if not games:
        send_telegram("🏒 Aucun match NHL aujourd'hui.")
        return

    # Une seule requête pour toutes les stats des équipes
    all_stats = get_all_standings()

    if not all_stats:
        send_telegram("⚠️ Impossible de récupérer les stats NHL aujourd'hui.")
        return

    send_telegram(f"🏒 NHL — Analyse du {today}\n📊 {len(games)} match(s) en cours d'analyse...")

    retenus = []

    for game in games:
        home_abbrev = game.get("homeTeam", {}).get("abbrev", "")
        away_abbrev = game.get("awayTeam", {}).get("abbrev", "")
        home_name   = game.get("homeTeam", {}).get("name", {}).get("default", home_abbrev)
        away_name   = game.get("awayTeam", {}).get("name", {}).get("default", away_abbrev)
        game_time   = game.get("startTimeUTC", "N/A")[:16].replace("T", " ")

        print(f"\n📊 {away_name} @ {home_name}")

        home_stats = all_stats.get(home_abbrev)
        away_stats = all_stats.get(away_abbrev)

        if passes_filter(home_stats, away_stats):
            print(f"   ✅ RETENU")
            match_info = {
                "home": home_name,
                "away": away_name,
                "date": today,
                "time": game_time
            }
            retenus.append(build_template(match_info, home_stats, away_stats))
        else:
            print(f"   ❌ REJETÉ")

    if retenus:
        send_telegram(f"✅ {len(retenus)} match(s) NHL retenu(s) aujourd'hui :")
        for t in retenus:
            send_telegram(t)
        send_telegram(
            "📎 Analyse ces matchs NHL pour Over/Under buts.\n"
            "Pour chaque match :\n"
            "1. Ligne recommandée (Over 5.5 ou Over 6.5)\n"
            "2. Probabilité Over + confiance (Fort / Moyen / Faible)\n"
            "3. Probabilité Under + confiance\n"
            "4. Points forts et risques\n"
            "5. Ta recommandation finale"
        )
    else:
        send_telegram("⚠️ Aucun match NHL ne passe les filtres aujourd'hui.")

    print(f"\n✅ Terminé — {len(retenus)} match(s) retenu(s)")


# ============================================================
# ▶️ LANCEMENT
# ============================================================

if __name__ == "__main__":
    lancer_analyse()
