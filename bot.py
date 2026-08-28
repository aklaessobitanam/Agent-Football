# ============================================================
# 🤖 AGENT IA v3 — NOUVEAUX MARCHÉS FOOTBALL
# ============================================================
# Marchés :
# 1. But dans chaque mi-temps
# 2. Nul dans au moins une mi-temps
# 3. But pendant le temps additionnel
# ============================================================

import requests
import json
import re
import time
import os
import math
from datetime import date

# ============================================================
# ⚙️ CONFIGURATION
# ============================================================

API_KEY        = os.environ.get("API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}

TARGET_LEAGUES = {
    39:  "Premier League (Angleterre)",
    140: "La Liga (Espagne)",
    135: "Serie A (Italie)",
    78:  "Bundesliga (Allemagne)",
    61:  "Ligue 1 (France)",
    88:  "Eredivisie (Pays-Bas)",
    94:  "Primeira Liga (Portugal)",
    144: "Jupiler Pro League (Belgique)",
    203: "Süper Lig (Turquie)",
    179: "Scottish Premiership",
    218: "Eliteserien (Norvège)",
    113: "Allsvenskan (Suède)",
    119: "Superliga (Danemark)",
    2:   "Champions League",
    3:   "Europa League",
    848: "Conference League",
    40:  "Championship (Angleterre D2)",
    79:  "2. Bundesliga (Allemagne D2)",
    136: "Serie B (Italie D2)",
    62:  "Ligue 2 (France D2)",
    141: "Segunda División (Espagne D2)",
    95:  "Liga Portugal 2 (Portugal D2)",
    204: "TFF First League (Turquie D2)",
    89:  "Eerste Divisie (Pays-Bas D2)",
}

# ============================================================
# 🎯 SEUILS PAR LIGUE — NOUVEAUX MARCHÉS
# ============================================================

DEFAULT_THRESHOLDS = {
    "both_halves_pct_min": 45,    # % estimé matchs avec but dans chaque MT
    "ht_draw_pct_min":     38,    # % estimé matchs avec nul dans au moins 1 MT
    "added_time_avg_min":  0.25,  # Total buts en TA par match (les deux équipes)
}

LEAGUE_THRESHOLDS = {
    # ── Très offensif ──
    78:  {"both_halves_pct_min": 52, "ht_draw_pct_min": 33, "added_time_avg_min": 0.28},  # Bundesliga
    88:  {"both_halves_pct_min": 52, "ht_draw_pct_min": 33, "added_time_avg_min": 0.28},  # Eredivisie
    119: {"both_halves_pct_min": 50, "ht_draw_pct_min": 35, "added_time_avg_min": 0.26},  # Superliga Danemark
    218: {"both_halves_pct_min": 50, "ht_draw_pct_min": 35, "added_time_avg_min": 0.26},  # Eliteserien Norvège
    79:  {"both_halves_pct_min": 50, "ht_draw_pct_min": 35, "added_time_avg_min": 0.26},  # 2. Bundesliga
    89:  {"both_halves_pct_min": 50, "ht_draw_pct_min": 35, "added_time_avg_min": 0.26},  # Eerste Divisie

    # ── Offensif ──
    39:  {"both_halves_pct_min": 48, "ht_draw_pct_min": 36, "added_time_avg_min": 0.27},  # Premier League
    179: {"both_halves_pct_min": 48, "ht_draw_pct_min": 36, "added_time_avg_min": 0.25},  # Scottish Premiership
    113: {"both_halves_pct_min": 48, "ht_draw_pct_min": 36, "added_time_avg_min": 0.25},  # Allsvenskan Suède
    40:  {"both_halves_pct_min": 46, "ht_draw_pct_min": 37, "added_time_avg_min": 0.26},  # Championship

    # ── Moyen ──
    140: {"both_halves_pct_min": 45, "ht_draw_pct_min": 38, "added_time_avg_min": 0.25},  # La Liga
    144: {"both_halves_pct_min": 45, "ht_draw_pct_min": 38, "added_time_avg_min": 0.25},  # Jupiler Belgique
    203: {"both_halves_pct_min": 45, "ht_draw_pct_min": 38, "added_time_avg_min": 0.25},  # Süper Lig Turquie
    94:  {"both_halves_pct_min": 45, "ht_draw_pct_min": 38, "added_time_avg_min": 0.25},  # Primeira Liga Portugal
    2:   {"both_halves_pct_min": 46, "ht_draw_pct_min": 37, "added_time_avg_min": 0.26},  # Champions League
    3:   {"both_halves_pct_min": 45, "ht_draw_pct_min": 38, "added_time_avg_min": 0.25},  # Europa League
    848: {"both_halves_pct_min": 45, "ht_draw_pct_min": 38, "added_time_avg_min": 0.25},  # Conference League
    141: {"both_halves_pct_min": 43, "ht_draw_pct_min": 39, "added_time_avg_min": 0.24},  # Segunda División
    95:  {"both_halves_pct_min": 43, "ht_draw_pct_min": 39, "added_time_avg_min": 0.24},  # Liga Portugal 2
    204: {"both_halves_pct_min": 43, "ht_draw_pct_min": 39, "added_time_avg_min": 0.24},  # TFF First League

    # ── Défensif ──
    135: {"both_halves_pct_min": 40, "ht_draw_pct_min": 40, "added_time_avg_min": 0.23},  # Serie A
    61:  {"both_halves_pct_min": 40, "ht_draw_pct_min": 40, "added_time_avg_min": 0.23},  # Ligue 1
    136: {"both_halves_pct_min": 38, "ht_draw_pct_min": 42, "added_time_avg_min": 0.22},  # Serie B
    62:  {"both_halves_pct_min": 38, "ht_draw_pct_min": 42, "added_time_avg_min": 0.22},  # Ligue 2
}

def get_thresholds(league_id):
    return LEAGUE_THRESHOLDS.get(league_id, DEFAULT_THRESHOLDS)

UNDERSTAT_LEAGUE_MAP = {
    39:  "EPL",
    140: "La_liga",
    135: "Serie_A",
    78:  "Bundesliga",
    61:  "Ligue_1",
}

api_calls = 0


# ============================================================
# 📲 TELEGRAM
# ============================================================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for i in range(0, len(message), 4096):
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": message[i:i+4096]}, timeout=10)
        except Exception as e:
            print(f"⚠️ Erreur Telegram : {e}")


# ============================================================
# 📡 API
# ============================================================

def api_call(endpoint, params):
    global api_calls
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, headers=HEADERS, params=params)
    api_calls += 1
    data = response.json()
    if data.get("errors"):
        return None
    return data.get("response", [])


def get_fixtures():
    today = date.today().strftime("%Y-%m-%d")
    result = api_call("fixtures", {"date": today})
    if not result:
        return []
    return [f for f in result
            if f["league"]["id"] in TARGET_LEAGUES
            and f["fixture"]["status"]["short"] in ["NS", "TBD"]]


def get_team_stats(team_id, league_id, season=2025):
    result = api_call("teams/statistics", {"team": team_id, "league": league_id, "season": season})
    if not result:
        result = api_call("teams/statistics", {"team": team_id, "league": league_id, "season": season - 1})
    return result if result else {}


def get_injuries(team_id, season=2025):
    result = api_call("injuries", {"team": team_id, "season": season})
    return result[:10] if result else []


def get_xg_understat(league_id, team_name, season=2024):
    league_str = UNDERSTAT_LEAGUE_MAP.get(league_id)
    if not league_str:
        return None, None
    url = f"https://understat.com/league/{league_str}/{season}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        match = re.search(r"var teamsData\s*=\s*JSON\.parse\('(.+?)'\)", resp.text)
        if not match:
            return None, None
        raw = match.group(1).encode('utf-8').decode('unicode_escape')
        teams_data = json.loads(raw)
        team_key = None
        for key, data in teams_data.items():
            understat_name = data.get("title", "").lower()
            if team_name.lower() in understat_name or understat_name in team_name.lower():
                team_key = key
                break
        if not team_key:
            return None, None
        history = teams_data[team_key].get("history", [])
        if not history:
            return None, None
        xg_for     = round(sum(float(m.get("xG",  0)) for m in history) / len(history), 2)
        xg_against = round(sum(float(m.get("xGA", 0)) for m in history) / len(history), 2)
        return xg_for, xg_against
    except:
        return None, None


# ============================================================
# 📊 TRAITEMENT
# ============================================================

def poisson_draw_prob(lambda1, lambda2, max_k=6):
    """P(X1 = X2) où X1~Poisson(λ1), X2~Poisson(λ2) — pour estimer P(nul dans une MT)"""
    prob = 0.0
    for k in range(max_k + 1):
        p1 = math.exp(-lambda1) * (lambda1 ** k) / math.factorial(k)
        p2 = math.exp(-lambda2) * (lambda2 ** k) / math.factorial(k)
        prob += p1 * p2
    return prob


def get_interval_goals(minute_data, intervals):
    total = 0
    for interval in intervals:
        total += int(minute_data.get(interval, {}).get("total", 0) or 0)
    return total


def extract_stats(team_stats, home_or_away):
    data = {
        "goals_for_avg":    0.0,
        "goals_against_avg":0.0,
        "played":           0,
        "form":             "N/A",
        "goals_1h_avg":     0.0,   # buts marqués en 1ère MT par match
        "goals_2h_avg":     0.0,   # buts marqués en 2ème MT par match
        "conceded_1h_avg":  0.0,   # buts encaissés en 1ère MT par match
        "conceded_2h_avg":  0.0,   # buts encaissés en 2ème MT par match
        "at_for_avg":       0.0,   # buts marqués en TA par match
    }

    if not team_stats:
        return data

    try:
        gf = team_stats.get("goals", {}).get("for",     {}).get("average", {})
        ga = team_stats.get("goals", {}).get("against", {}).get("average", {})
        data["goals_for_avg"]     = float(gf.get(home_or_away, gf.get("total", 0)) or 0)
        data["goals_against_avg"] = float(ga.get(home_or_away, ga.get("total", 0)) or 0)

        played = team_stats.get("fixtures", {}).get("played", {})
        data["played"] = int(played.get("total", 0) or 0)

        form_full = team_stats.get("form", "")
        data["form"] = form_full[-5:] if form_full else "N/A"

        if data["played"] > 0:
            n = data["played"]
            mins_for     = team_stats.get("goals", {}).get("for",     {}).get("minute", {})
            mins_against = team_stats.get("goals", {}).get("against", {}).get("minute", {})

            gf_1h = get_interval_goals(mins_for,     ["0-15", "16-30", "31-45"])
            gf_2h = get_interval_goals(mins_for,     ["46-60", "61-75", "76-90"])
            gf_at = get_interval_goals(mins_for,     ["91-105", "106-120"])
            ga_1h = get_interval_goals(mins_against, ["0-15", "16-30", "31-45"])
            ga_2h = get_interval_goals(mins_against, ["46-60", "61-75", "76-90"])

            data["goals_1h_avg"]    = round(gf_1h / n, 3)
            data["goals_2h_avg"]    = round(gf_2h / n, 3)
            data["conceded_1h_avg"] = round(ga_1h / n, 3)
            data["conceded_2h_avg"] = round(ga_2h / n, 3)
            data["at_for_avg"]      = round(gf_at / n, 3)

    except Exception as e:
        print(f"  ⚠️ Erreur extraction : {e}")

    return data


def extract_absents(injuries_data):
    if not injuries_data:
        return "Aucune donnée"
    absents = [f"{inj.get('player',{}).get('name','?')} ({inj.get('player',{}).get('reason','N/A')})"
               for inj in injuries_data[:5]]
    return ", ".join(absents) if absents else "Aucun absent signalé"


def compute_match_probs(home_data, away_data):
    """Calcule les probabilités pour les 3 marchés via Poisson"""

    # ── Marché 1 : But dans chaque mi-temps ──
    lam_1h = home_data["goals_1h_avg"] + away_data["goals_1h_avg"]
    lam_2h = home_data["goals_2h_avg"] + away_data["goals_2h_avg"]
    p_goal_1h    = (1 - math.exp(-lam_1h)) * 100
    p_goal_2h    = (1 - math.exp(-lam_2h)) * 100
    p_both_halves = p_goal_1h * p_goal_2h / 100

    # ── Marché 2 : Nul dans au moins une mi-temps ──
    p_draw_1h = poisson_draw_prob(home_data["goals_1h_avg"], away_data["goals_1h_avg"]) * 100
    p_draw_2h = poisson_draw_prob(home_data["goals_2h_avg"], away_data["goals_2h_avg"]) * 100
    p_ht_draw = 100 - (1 - p_draw_1h/100) * (1 - p_draw_2h/100) * 100

    # ── Marché 3 : But en temps additionnel ──
    at_total_avg = home_data["at_for_avg"] + away_data["at_for_avg"]
    p_at_goal    = (1 - math.exp(-at_total_avg)) * 100

    return {
        "both_halves_pct": round(p_both_halves, 1),
        "ht_draw_pct":     round(p_ht_draw, 1),
        "at_total_avg":    round(at_total_avg, 3),
        "at_goal_pct":     round(p_at_goal, 1),
        "p_goal_1h":       round(p_goal_1h, 1),
        "p_goal_2h":       round(p_goal_2h, 1),
        "p_draw_1h":       round(p_draw_1h, 1),
        "p_draw_2h":       round(p_draw_2h, 1),
    }


# ============================================================
# 🔍 FILTRE
# ============================================================

def passes_filter(home_data, away_data, league_id):
    t     = get_thresholds(league_id)
    probs = compute_match_probs(home_data, away_data)
    score = 0

    if probs["both_halves_pct"] >= t["both_halves_pct_min"]:
        score += 1
    if probs["ht_draw_pct"] >= t["ht_draw_pct_min"]:
        score += 1
    if probs["at_total_avg"] >= t["added_time_avg_min"]:
        score += 1

    return score >= 2, probs


# ============================================================
# 📋 TEMPLATE
# ============================================================

def build_template(match_info, home_data, away_data, probs,
                   home_absents, away_absents,
                   xg_hf, xg_ha, xg_af, xg_aa, thresholds):

    def fmt_xg(val):
        return f"{val} (Understat)" if val is not None else "N/A"

    return f"""
========================================
Match : {match_info['home']} vs {match_info['away']}
Ligue : {match_info['league']}
Date  : {match_info['date']} | Heure : {match_info['time']}
========================================
{match_info['home']} (Domicile) :
- Buts marqués (moy.)         : {home_data['goals_for_avg']:.2f}
- Buts encaissés (moy.)       : {home_data['goals_against_avg']:.2f}
- xG for                      : {fmt_xg(xg_hf)}
- xG against                  : {fmt_xg(xg_ha)}
- Buts marqués 1ère MT (moy.) : {home_data['goals_1h_avg']:.3f}
- Buts marqués 2ème MT (moy.) : {home_data['goals_2h_avg']:.3f}
- Buts en TA (moy.)           : {home_data['at_for_avg']:.3f}

{match_info['away']} (Extérieur) :
- Buts marqués (moy.)         : {away_data['goals_for_avg']:.2f}
- Buts encaissés (moy.)       : {away_data['goals_against_avg']:.2f}
- xG for                      : {fmt_xg(xg_af)}
- xG against                  : {fmt_xg(xg_aa)}
- Buts marqués 1ère MT (moy.) : {away_data['goals_1h_avg']:.3f}
- Buts marqués 2ème MT (moy.) : {away_data['goals_2h_avg']:.3f}
- Buts en TA (moy.)           : {away_data['at_for_avg']:.3f}

Probabilités estimées (Poisson) :
── But dans chaque mi-temps ──
- P(but en 1ère MT)           : {probs['p_goal_1h']:.1f}%
- P(but en 2ème MT)           : {probs['p_goal_2h']:.1f}%
- P(but dans CHAQUE MT)       : {probs['both_halves_pct']:.1f}%

── Nul dans au moins une MT ──
- P(nul en 1ère MT)           : {probs['p_draw_1h']:.1f}%
- P(nul en 2ème MT)           : {probs['p_draw_2h']:.1f}%
- P(nul dans AU MOINS 1 MT)   : {probs['ht_draw_pct']:.1f}%

── But en temps additionnel ──
- Buts TA / match (combiné)   : {probs['at_total_avg']:.3f}
- P(but en TA)                : {probs['at_goal_pct']:.1f}%

Contexte :
- Forme {match_info['home']} (5 derniers) : {home_data['form']}
- Forme {match_info['away']} (5 derniers) : {away_data['form']}
- Absents {match_info['home']}             : {home_absents}
- Absents {match_info['away']}             : {away_absents}
- Seuils : Both halves≥{thresholds['both_halves_pct_min']}% | HT Draw≥{thresholds['ht_draw_pct_min']}% | TA≥{thresholds['added_time_avg_min']}
========================================"""


# ============================================================
# 🚀 ANALYSE PRINCIPALE
# ============================================================

def lancer_analyse():
    today    = date.today().strftime("%Y-%m-%d")
    fixtures = get_fixtures()

    if not fixtures:
        send_telegram("❌ Aucun match trouvé aujourd'hui dans les ligues ciblées.")
        return

    send_telegram(f"🤖 Analyse du {today}\n📊 {len(fixtures)} matchs en cours d'analyse...")

    retenus = []

    for fixture in fixtures:
        fid         = fixture["fixture"]["id"]
        home        = fixture["teams"]["home"]
        away        = fixture["teams"]["away"]
        league      = fixture["league"]
        heure       = fixture["fixture"]["date"][11:16]
        league_id   = league["id"]
        league_name = TARGET_LEAGUES.get(league_id, league["name"])
        season      = league.get("season", 2025)

        home_stats = get_team_stats(home["id"], league_id, season)
        away_stats = get_team_stats(away["id"], league_id, season)
        time.sleep(0.3)

        home_data = extract_stats(home_stats, "home")
        away_data = extract_stats(away_stats, "away")

        passes, probs = passes_filter(home_data, away_data, league_id)

        if passes:
            home_absents = extract_absents(get_injuries(home["id"], season))
            away_absents = extract_absents(get_injuries(away["id"], season))
            xg_hf, xg_ha = get_xg_understat(league_id, home["name"], season - 1)
            xg_af, xg_aa = get_xg_understat(league_id, away["name"], season - 1)

            match_info = {
                "home": home["name"], "away": away["name"],
                "league": league_name, "date": today, "time": heure
            }
            thresholds = get_thresholds(league_id)
            retenus.append(build_template(
                match_info, home_data, away_data, probs,
                home_absents, away_absents,
                xg_hf, xg_ha, xg_af, xg_aa, thresholds
            ))

    if retenus:
        send_telegram(f"✅ {len(retenus)} match(s) retenu(s) aujourd'hui :")
        for t in retenus:
            send_telegram(t)
        send_telegram(
            "📎 Analyse ces matchs pour les 3 marchés suivants :\n\n"
            "1. But dans chaque mi-temps\n"
            "   → Probabilité + confiance (Fort/Moyen/Faible)\n\n"
            "2. Nul dans au moins une mi-temps\n"
            "   → Probabilité + confiance\n\n"
            "3. But pendant le temps additionnel\n"
            "   → Probabilité + confiance\n\n"
            "Pour chaque match, donne ta meilleure sélection.\n"
            "À la fin, propose un combiné de 2-3 sélections maximum."
        )
    else:
        send_telegram("⚠️ Aucun match ne passe les filtres aujourd'hui.")

    print(f"✅ Terminé — {len(retenus)} match(s) | {api_calls} appels API")


# ============================================================
# ▶️ LANCEMENT
# ============================================================

if __name__ == "__main__":
    lancer_analyse()
