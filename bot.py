# ============================================================
# 🤖 AGENT IA v2 — VERSION GITHUB ACTIONS
# ============================================================

import requests
import json
import re
import time
import os
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
    # ── Deuxièmes divisions ──
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
# 🎯 SEUILS PAR LIGUE
# ============================================================

DEFAULT_THRESHOLDS = {
    "btts_pct_min": 55,
    "over15_pct_min": 70,
    "xg_total_min": 2.2,
    "combined_goals_avg_min": 2.0
}

LEAGUE_THRESHOLDS = {
    # ── Très offensif ──
    78:  {"btts_pct_min": 62, "over15_pct_min": 78, "xg_total_min": 2.6, "combined_goals_avg_min": 2.4},  # Bundesliga
    88:  {"btts_pct_min": 62, "over15_pct_min": 78, "xg_total_min": 2.6, "combined_goals_avg_min": 2.4},  # Eredivisie
    119: {"btts_pct_min": 60, "over15_pct_min": 75, "xg_total_min": 2.5, "combined_goals_avg_min": 2.3},  # Superliga Danemark
    218: {"btts_pct_min": 60, "over15_pct_min": 75, "xg_total_min": 2.5, "combined_goals_avg_min": 2.3},  # Eliteserien Norvège
    79:  {"btts_pct_min": 58, "over15_pct_min": 73, "xg_total_min": 2.4, "combined_goals_avg_min": 2.2},  # 2. Bundesliga
    89:  {"btts_pct_min": 58, "over15_pct_min": 73, "xg_total_min": 2.4, "combined_goals_avg_min": 2.2},  # Eerste Divisie

    # ── Offensif ──
    39:  {"btts_pct_min": 58, "over15_pct_min": 73, "xg_total_min": 2.4, "combined_goals_avg_min": 2.2},  # Premier League
    179: {"btts_pct_min": 58, "over15_pct_min": 73, "xg_total_min": 2.4, "combined_goals_avg_min": 2.2},  # Scottish Premiership
    113: {"btts_pct_min": 58, "over15_pct_min": 73, "xg_total_min": 2.4, "combined_goals_avg_min": 2.2},  # Allsvenskan Suède
    40:  {"btts_pct_min": 55, "over15_pct_min": 70, "xg_total_min": 2.2, "combined_goals_avg_min": 2.0},  # Championship

    # ── Moyen ──
    140: {"btts_pct_min": 55, "over15_pct_min": 70, "xg_total_min": 2.2, "combined_goals_avg_min": 2.0},  # La Liga
    144: {"btts_pct_min": 55, "over15_pct_min": 70, "xg_total_min": 2.2, "combined_goals_avg_min": 2.0},  # Jupiler Belgique
    203: {"btts_pct_min": 55, "over15_pct_min": 70, "xg_total_min": 2.2, "combined_goals_avg_min": 2.0},  # Süper Lig Turquie
    94:  {"btts_pct_min": 55, "over15_pct_min": 70, "xg_total_min": 2.2, "combined_goals_avg_min": 2.0},  # Primeira Liga Portugal
    2:   {"btts_pct_min": 55, "over15_pct_min": 70, "xg_total_min": 2.3, "combined_goals_avg_min": 2.1},  # Champions League
    3:   {"btts_pct_min": 55, "over15_pct_min": 70, "xg_total_min": 2.2, "combined_goals_avg_min": 2.0},  # Europa League
    848: {"btts_pct_min": 55, "over15_pct_min": 70, "xg_total_min": 2.2, "combined_goals_avg_min": 2.0},  # Conference League
    141: {"btts_pct_min": 52, "over15_pct_min": 67, "xg_total_min": 2.1, "combined_goals_avg_min": 1.9},  # Segunda División
    95:  {"btts_pct_min": 52, "over15_pct_min": 67, "xg_total_min": 2.1, "combined_goals_avg_min": 1.9},  # Liga Portugal 2
    204: {"btts_pct_min": 52, "over15_pct_min": 67, "xg_total_min": 2.1, "combined_goals_avg_min": 1.9},  # TFF First League

    # ── Défensif ──
    135: {"btts_pct_min": 50, "over15_pct_min": 65, "xg_total_min": 2.0, "combined_goals_avg_min": 1.8},  # Serie A
    61:  {"btts_pct_min": 50, "over15_pct_min": 65, "xg_total_min": 2.0, "combined_goals_avg_min": 1.8},  # Ligue 1
    136: {"btts_pct_min": 48, "over15_pct_min": 63, "xg_total_min": 1.9, "combined_goals_avg_min": 1.7},  # Serie B
    62:  {"btts_pct_min": 48, "over15_pct_min": 63, "xg_total_min": 1.9, "combined_goals_avg_min": 1.7},  # Ligue 2
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
            requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": message[i:i+4096]
            }, timeout=10)
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


def get_prediction(fixture_id):
    result = api_call("predictions", {"fixture": fixture_id})
    return result[0] if result else None


def get_injuries(team_id, season=2025):
    result = api_call("injuries", {"team": team_id, "season": season})
    return result[:10] if result else []


# ============================================================
# 📊 TRAITEMENT
# ============================================================

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


def extract_stats(team_stats, home_or_away):
    data = {"goals_for_avg": 0.0, "goals_against_avg": 0.0, "played": 0,
            "clean_sheets": 0, "failed_to_score": 0, "form": "N/A",
            "btts_pct": 0.0, "over15_pct": 0.0}
    if not team_stats:
        return data
    try:
        gf = team_stats.get("goals", {}).get("for",     {}).get("average", {})
        ga = team_stats.get("goals", {}).get("against", {}).get("average", {})
        data["goals_for_avg"]     = float(gf.get(home_or_away, gf.get("total", 0)) or 0)
        data["goals_against_avg"] = float(ga.get(home_or_away, ga.get("total", 0)) or 0)
        data["played"]            = int(team_stats.get("fixtures",        {}).get("played",  {}).get("total", 0) or 0)
        data["clean_sheets"]      = int(team_stats.get("clean_sheet",     {}).get("total", 0) or 0)
        data["failed_to_score"]   = int(team_stats.get("failed_to_score", {}).get("total", 0) or 0)
        form_full = team_stats.get("form", "")
        data["form"] = form_full[-5:] if form_full else "N/A"
        if data["played"] > 0:
            scores_pct   = 1 - (data["failed_to_score"] / data["played"])
            concedes_pct = 1 - (data["clean_sheets"]    / data["played"])
            data["btts_pct"]   = round(scores_pct * concedes_pct * 100, 1)
            avg_total          = data["goals_for_avg"] + data["goals_against_avg"]
            data["over15_pct"] = round(min(avg_total / 2.5, 1.0) * 100, 1)
    except:
        pass
    return data


def extract_xg_api(prediction, side):
    if not prediction:
        return "N/A"
    try:
        goals = prediction.get("predictions", {}).get("goals", {})
        val   = goals.get(side, None)
        return str(val).replace("-", "~") if val else "N/A"
    except:
        return "N/A"


def extract_absents(injuries_data):
    if not injuries_data:
        return "Aucune donnée"
    absents = [f"{inj.get('player',{}).get('name','?')} ({inj.get('player',{}).get('reason','N/A')})"
               for inj in injuries_data[:5]]
    return ", ".join(absents) if absents else "Aucun absent signalé"


def passes_filter(home_data, away_data, prediction, league_id):
    t = get_thresholds(league_id)
    score = 0
    if home_data["goals_for_avg"] + away_data["goals_for_avg"] >= t["combined_goals_avg_min"]:
        score += 1
    if (home_data["btts_pct"] + away_data["btts_pct"]) / 2 >= t["btts_pct_min"]:
        score += 1
    if (home_data["over15_pct"] + away_data["over15_pct"]) / 2 >= t["over15_pct_min"]:
        score += 1
    if prediction:
        try:
            goals  = prediction.get("predictions", {}).get("goals", {})
            xg_tot = abs(float(str(goals.get("home", "0")).replace("-", ""))) + \
                     abs(float(str(goals.get("away", "0")).replace("-", "")))
            if xg_tot >= t["xg_total_min"]:
                score += 1
        except:
            pass
    return score >= 3


def build_template(match_info, home_data, away_data, prediction,
                   home_absents, away_absents,
                   xg_hf, xg_ha, xg_af, xg_aa, thresholds):

    def fmt(val, fallback):
        return f"{val} (Understat)" if val is not None else (fallback or "N/A")

    return f"""
========================================
Match : {match_info['home']} vs {match_info['away']}
Ligue : {match_info['league']}
Date  : {match_info['date']} | Heure : {match_info['time']}
Seuils ligue : BTTS≥{thresholds['btts_pct_min']}% | Over1.5≥{thresholds['over15_pct_min']}% | xG≥{thresholds['xg_total_min']}
========================================
{match_info['home']} (Domicile) :
- Buts marqués (moy.)   : {home_data['goals_for_avg']:.2f}
- Buts encaissés (moy.) : {home_data['goals_against_avg']:.2f}
- xG for                : {fmt(xg_hf, extract_xg_api(prediction, 'home'))}
- xG against            : {fmt(xg_ha, None)}
- BTTS %                : {home_data['btts_pct']:.1f}%
- Over 1.5 %            : {home_data['over15_pct']:.1f}%

{match_info['away']} (Extérieur) :
- Buts marqués (moy.)   : {away_data['goals_for_avg']:.2f}
- Buts encaissés (moy.) : {away_data['goals_against_avg']:.2f}
- xG for                : {fmt(xg_af, extract_xg_api(prediction, 'away'))}
- xG against            : {fmt(xg_aa, None)}
- BTTS %                : {away_data['btts_pct']:.1f}%
- Over 1.5 %            : {away_data['over15_pct']:.1f}%

Contexte :
- Forme {match_info['home']} (5 derniers) : {home_data['form']}
- Forme {match_info['away']} (5 derniers) : {away_data['form']}
- Absents {match_info['home']} : {home_absents}
- Absents {match_info['away']} : {away_absents}
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
        prediction = get_prediction(fid)
        time.sleep(0.3)

        home_data = extract_stats(home_stats, "home")
        away_data = extract_stats(away_stats, "away")

        if passes_filter(home_data, away_data, prediction, league_id):
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
                match_info, home_data, away_data, prediction,
                home_absents, away_absents,
                xg_hf, xg_ha, xg_af, xg_aa, thresholds
            ))

    if retenus:
        send_telegram(f"✅ {len(retenus)} match(s) retenu(s) aujourd'hui :")
        for t in retenus:
            send_telegram(t)
        send_telegram(
            "📎 Analyse ces matchs pour BTTS et Over 1.5.\n"
            "Pour chaque match :\n"
            "1. Probabilité BTTS + confiance\n"
            "2. Probabilité Over 1.5 + confiance\n"
            "3. Points forts et risques\n"
            "4. Recommandation finale"
        )
    else:
        send_telegram("⚠️ Aucun match ne passe les filtres aujourd'hui.")

    print(f"✅ Terminé — {len(retenus)} match(s) | {api_calls} appels API")


# ============================================================
# ▶️ LANCEMENT
# ============================================================

if __name__ == "__main__":
    lancer_analyse()
