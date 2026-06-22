from typing import Any, Optional
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd
import httpx
import os
import numpy as np
from sklearn.linear_model import LogisticRegression

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="IPL Prediction Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

MODEL_DIR = "models"
TOSS_MODEL_PATH = os.path.join(MODEL_DIR, "toss_model.pkl")
MATCH_MODEL_PATH = os.path.join(MODEL_DIR, "match_model.pkl")
CRIC_API_KEY = os.environ.get("CRIC_API_KEY", "")
DEFAULT_SCHEDULE_URL = os.environ.get("SCHEDULE_API_URL", "")
MODELS_LOADED = False

toss_model = None
match_model = None


def build_team_stats() -> dict:
    return {
        "Mumbai Indians": 0.55,
        "Chennai Super Kings": 0.58,
        "Royal Challengers Bengaluru": 0.48,
        "Gujarat Titans": 0.60,
        "Lucknow Super Giants": 0.52,
        "Rajasthan Royals": 0.51,
        "Kolkata Knight Riders": 0.53,
        "Sunrisers Hyderabad": 0.49,
        "Delhi Capitals": 0.45,
        "Punjab Kings": 0.44,
    }


def train_synthetic_models():
    np.random.seed(42)
    team_stats = build_team_stats()
    teams = list(team_stats.keys())
    data = []

    for _ in range(1000):
        team1, team2 = np.random.choice(teams, size=2, replace=False)
        team1_toss_pct = team_stats[team1]
        team2_toss_pct = team_stats[team2]

        toss_prob = team1_toss_pct / (team1_toss_pct + team2_toss_pct)
        team1_toss = int(np.random.random() < toss_prob)

        match_prob = (team1_toss_pct * 0.6 + team1_toss * 0.1) / (team1_toss_pct * 0.6 + team2_toss_pct * 0.6 + 0.1)
        match_team1 = int(np.random.random() < match_prob)

        data.append(
            {
                "team1": team1,
                "team2": team2,
                "team1_toss_pct": team1_toss_pct,
                "team2_toss_pct": team2_toss_pct,
                "team1_toss": team1_toss,
                "match_team1": match_team1,
            }
        )

    df = pd.DataFrame(data)
    X_toss = df[["team1_toss_pct", "team2_toss_pct"]]
    y_toss = df["team1_toss"]
    X_match = df[["team1_toss", "team1_toss_pct", "team2_toss_pct"]]
    y_match = df["match_team1"]

    toss_model = LogisticRegression(max_iter=200)
    match_model = LogisticRegression(max_iter=200)
    toss_model.fit(X_toss, y_toss)
    match_model.fit(X_match, y_match)

    return toss_model, match_model


def save_models(toss_model: LogisticRegression, match_model: LogisticRegression):
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(toss_model, TOSS_MODEL_PATH)
    joblib.dump(match_model, MATCH_MODEL_PATH)


def load_or_train_models():
    global toss_model, match_model, MODELS_LOADED
    try:
        toss_model = joblib.load(TOSS_MODEL_PATH)
        match_model = joblib.load(MATCH_MODEL_PATH)
        MODELS_LOADED = True
    except Exception:
        toss_model, match_model = train_synthetic_models()
        save_models(toss_model, match_model)
        MODELS_LOADED = True


def normalize_match_entry(entry: dict) -> Optional[dict]:
    team1 = entry.get("team1") or entry.get("teamA") or entry.get("homeTeam") or (entry.get("teams") or [None, None])[0]
    team2 = entry.get("team2") or entry.get("teamB") or entry.get("awayTeam") or (entry.get("teams") or [None, None])[1]
    if not team1 or not team2:
        return None

    name = str(entry.get("name", "")).lower()
    match_type = str(entry.get("matchType", "")).lower()
    if "ipl" not in name and "ipl" not in match_type and "t20" not in match_type:
        return None

    toss_winner = entry.get("toss_winner") or entry.get("tossWinner") or entry.get("toss_winner_team")
    if toss_winner and toss_winner not in [team1, team2]:
        toss_winner = None

    winner = entry.get("winner") or entry.get("matchWinner") or entry.get("result")
    if winner and winner not in [team1, team2]:
        winner = None

    status = str(entry.get("status", "")).lower()
    is_completed = status in ["completed", "finished", "ended", "result"] or bool(winner)

    toss_team1 = None
    if toss_winner:
        toss_team1 = 1 if toss_winner == team1 else 0

    return {
        "team1": team1,
        "team2": team2,
        "venue": entry.get("venue") or entry.get("ground") or "TBA",
        "date": entry.get("date") or entry.get("startDate") or "TBA",
        "winner": winner,
        "toss_team1": toss_team1,
        "is_completed": is_completed,
    }


def parse_schedule_payload(payload: Any) -> list:
    if isinstance(payload, dict):
        for root in ["schedule", "matches", "data", "fixtures"]:
            if root in payload and isinstance(payload[root], list):
                payload = payload[root]
                break

    if not isinstance(payload, list):
        raise ValueError("Schedule payload must be a JSON array or an object containing a list under schedule, matches, data, or fixtures.")

    matches = []
    for item in payload:
        normalized = normalize_match_entry(item)
        if normalized:
            matches.append(normalized)
    return matches


def add_team_strengths(df: pd.DataFrame) -> pd.DataFrame:
    stats = build_team_stats()
    df["team1_toss_pct"] = df["team1"].map(stats).fillna(0.5)
    df["team2_toss_pct"] = df["team2"].map(stats).fillna(0.5)
    return df


def generate_predictions(matches: list) -> dict:
    if not matches:
        raise ValueError("No valid IPL matches were found in the provided schedule.")

    df = pd.DataFrame(matches)
    df = add_team_strengths(df)

    if "toss_team1" not in df.columns:
        df["toss_team1"] = np.nan

    unknown_toss = df["toss_team1"].isna()
    if unknown_toss.any():
        toss_input = df.loc[unknown_toss, ["team1_toss_pct", "team2_toss_pct"]]
        df.loc[unknown_toss, "toss_team1"] = toss_model.predict(toss_input)

    df["predicted_toss_winner"] = np.where(df["toss_team1"] == 1, df["team1"], df["team2"])
    df["team1_toss"] = (df["predicted_toss_winner"] == df["team1"]).astype(int)

    if "winner" not in df.columns:
        df["winner"] = None

    unknown_match = df["winner"].isna()
    df["predicted_match_team1"] = np.nan
    if unknown_match.any():
        match_input = df.loc[unknown_match, ["team1_toss", "team1_toss_pct", "team2_toss_pct"]]
        df.loc[unknown_match, "predicted_match_team1"] = match_model.predict(match_input)

    df.loc[~unknown_match, "predicted_match_team1"] = np.where(df.loc[~unknown_match, "winner"] == df.loc[~unknown_match, "team1"], 1, 0)
    df["predicted_match_winner"] = np.where(df["predicted_match_team1"] == 1, df["team1"], df["team2"])
    df["result_source"] = np.where(df["winner"].notna(), "actual", "prediction")

    expected_wins = df["predicted_match_winner"].value_counts().to_dict()
    trophy_winner = max(expected_wins.items(), key=lambda item: item[1])[0] if expected_wins else "Unknown"

    return {
        "trophy_winner": trophy_winner,
        "win_distribution": expected_wins,
        "matches": df[["date", "venue", "team1", "team2", "predicted_toss_winner", "predicted_match_winner", "winner", "result_source"]].to_dict(orient="records"),
    }


class SchedulePayload(BaseModel):
    schedule: Optional[list] = None


async def fetch_json(url: str) -> Any:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


@app.on_event("startup")
def startup_event():
    load_or_train_models()


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/predict/upcoming")
async def predict_upcoming_matches(schedule_url: Optional[str] = None):
    if not MODELS_LOADED:
        raise HTTPException(status_code=500, detail="Models not loaded.")

    if schedule_url:
        raw_payload = await fetch_json(schedule_url)
    elif DEFAULT_SCHEDULE_URL:
        raw_payload = await fetch_json(DEFAULT_SCHEDULE_URL)
    elif CRIC_API_KEY:
        raw_payload = await fetch_json(f"https://api.cricapi.com/v1/matches?apikey={CRIC_API_KEY}&offset=0")
    else:
        raise HTTPException(status_code=400, detail="Provide schedule_url or configure CRIC_API_KEY or SCHEDULE_API_URL.")

    matches = parse_schedule_payload(raw_payload)
    if not matches:
        raise HTTPException(status_code=400, detail="Could not parse any IPL matches from the schedule data.")

    return generate_predictions(matches)


@app.post("/predict/schedule")
async def predict_from_schedule(payload: SchedulePayload = Body(...)):
    if not MODELS_LOADED:
        raise HTTPException(status_code=500, detail="Models not loaded.")

    if not payload.schedule:
        raise HTTPException(status_code=400, detail="Please include a 'schedule' array in the JSON body.")

    matches = parse_schedule_payload(payload.schedule)
    if not matches:
        raise HTTPException(status_code=400, detail="Could not parse any IPL matches from the provided schedule.")

    return generate_predictions(matches)


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": MODELS_LOADED}
