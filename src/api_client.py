"""
API-Football Client
====================
Zero-dependency REST client for api-football (api-sports.io).
All HTTP via Python stdlib urllib — no pip install needed.

Endpoints used (v3):
  /teams?league=1&season=2026            — 48 World Cup teams
  /players/squads?team=X              — Squad roster per team
  /players?league=1&season=2026&page=N — Player season stats
  /fixtures?league=1&season=2026      — Full match schedule
  /fixtures/players?fixture=X         — Player ratings per match
  /injuries?league=1&season=2026      — Injury reports
  /standings?league=1&season=2026     — Group standings
"""
import json
import time
import os
import urllib.request
import urllib.error
from typing import Optional, Dict, List, Any


# ============================================================================
# Configuration
# ============================================================================

API_BASE = "https://v3.football.api-sports.io"
API_HEADERS = {
    "x-apisports-key": "c26d1135c7286baae19fa141e5119317",
    "Content-Type": "application/json",
}
REQUEST_DELAY = 1.1  # seconds between requests (rate limiting safety)

# World Cup 2026 identifiers
WORLD_CUP_LEAGUE_ID = 1
WORLD_CUP_SEASON = 2026


# ============================================================================
# API Client
# ============================================================================

class ApiFootballClient:
    """REST client for API-Football v3. Uses only Python stdlib."""

    def __init__(self, api_key: str = None):
        if api_key:
            self.set_key(api_key)
        self._last_request = 0.0
        self.stats = {"requests_today": 0, "last_reset": time.time()}

    def set_key(self, api_key: str):
        """Set or update the API key."""
        API_HEADERS["x-apisports-key"] = api_key

    def is_configured(self) -> bool:
        """Check if a real API key has been set."""
        key = API_HEADERS.get("x-apisports-key", "")
        return key not in ("", "YOUR_API_KEY_HERE")

    # ------------------------------------------------------------------
    # Low-level request
    # ------------------------------------------------------------------

    def _request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[dict]:
        """Make a GET request to the API-Football v3 endpoint."""
        if not self.is_configured():
            print(f"  [API] Skipping {endpoint} — no API key configured")
            return None

        elapsed = time.time() - self._last_request
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)

        url = API_BASE + endpoint
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            url += "?" + query

        try:
            req = urllib.request.Request(url, headers=API_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                self._last_request = time.time()
                self.stats["requests_today"] += 1
                return data
        except urllib.error.HTTPError as e:
            print(f"  [API] HTTP {e.code} on {endpoint}: {e.reason}")
            if e.code == 403:
                print("  [API] API key invalid or quota exceeded")
            return None
        except Exception as e:
            print(f"  [API] Request failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    def get_teams(self) -> List[dict]:
        """Get all 48 World Cup 2026 teams."""
        data = self._request("/teams", {"league": WORLD_CUP_LEAGUE_ID, "season": WORLD_CUP_SEASON})
        if not data or "response" not in data:
            return []
        return data["response"]

    # ------------------------------------------------------------------
    # Squads
    # ------------------------------------------------------------------

    def get_squad(self, team_id: int) -> List[dict]:
        """Get the squad roster for a team."""
        data = self._request("/players/squads", {"team": team_id})
        if not data or "response" not in data:
            return []
        if data["response"] and len(data["response"]) > 0:
            return data["response"][0].get("players", [])
        return []

    # ------------------------------------------------------------------
    # Player Season Stats
    # ------------------------------------------------------------------

    def get_players(self, team_id: int = None, page: int = 1) -> dict:
        """Get player season statistics."""
        params = {"league": WORLD_CUP_LEAGUE_ID, "season": WORLD_CUP_SEASON, "page": page}
        if team_id:
            params["team"] = team_id
        data = self._request("/players", params)
        if not data:
            return {"response": [], "paging": {}}
        return data

    def get_all_players(self, team_id: int = None) -> List[dict]:
        """Get ALL player stats across all pages."""
        all_players = []
        page = 1
        while True:
            result = self.get_players(team_id=team_id, page=page)
            players = result.get("response", [])
            if not players:
                break
            all_players.extend(players)
            paging = result.get("paging", {})
            total_pages = paging.get("total", 1)
            if page >= total_pages:
                break
            page += 1
        return all_players

    # ------------------------------------------------------------------
    # Fixtures (Match Schedule & Results)
    # ------------------------------------------------------------------

    def get_fixtures(
        self,
        team_id: int = None,
        status: str = None,
        date_from: str = None,
        date_to: str = None,
        live: str = None,
        season: int = WORLD_CUP_SEASON,
    ) -> List[dict]:
        """Get match fixtures."""
        params = {"league": WORLD_CUP_LEAGUE_ID, "season": season}
        if team_id:
            params["team"] = team_id
        if status:
            params["status"] = status
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        if live:
            params["live"] = live

        data = self._request("/fixtures", params)
        if not data or "response" not in data:
            return []
        return data["response"]

    def get_fixture_detail(self, fixture_id: int) -> Optional[dict]:
        """Get detailed info for a specific fixture."""
        data = self._request("/fixtures", {"id": fixture_id})
        if data and "response" in data and data["response"]:
            return data["response"][0]
        return None

    def get_live_fixtures(self) -> List[dict]:
        """Get all currently live World Cup matches."""
        return self.get_fixtures(live="all")

    def get_recent_results(self, days_back: int = 3) -> List[dict]:
        """Get completed matches from recent days."""
        from datetime import datetime, timedelta
        today = datetime.now()
        date_to = today.strftime("%Y-%m-%d")
        date_from = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        return self.get_fixtures(status="FT", date_from=date_from, date_to=date_to)

    def get_upcoming_fixtures(self, days_ahead: int = 2) -> List[dict]:
        """Get upcoming scheduled matches."""
        from datetime import datetime, timedelta
        today = datetime.now()
        date_from = today.strftime("%Y-%m-%d")
        date_to = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        return self.get_fixtures(status="NS", date_from=date_from, date_to=date_to)

    # ------------------------------------------------------------------
    # Player Match Ratings
    # ------------------------------------------------------------------

    def get_fixture_player_stats(self, fixture_id: int) -> List[dict]:
        """Get player ratings/stats for a specific fixture."""
        data = self._request("/fixtures/players", {"fixture": fixture_id})
        if not data or "response" not in data:
            return []
        return data["response"]

    # ------------------------------------------------------------------
    # Injuries
    # ------------------------------------------------------------------

    def get_injuries(self, team_id: int = None) -> List[dict]:
        """Get injury/suspension reports."""
        params = {"league": WORLD_CUP_LEAGUE_ID, "season": WORLD_CUP_SEASON}
        if team_id:
            params["team"] = team_id
        data = self._request("/injuries", params)
        if not data or "response" not in data:
            return []
        return data["response"]

    # ------------------------------------------------------------------
    # Standings
    # ------------------------------------------------------------------

    def get_standings(self) -> List[dict]:
        """Get World Cup group standings."""
        data = self._request("/standings", {
            "league": WORLD_CUP_LEAGUE_ID,
            "season": WORLD_CUP_SEASON,
        })
        if not data or "response" not in data:
            return []
        standings = []
        for entry in data["response"]:
            league_data = entry.get("league", {})
            groups = league_data.get("standings", [])
            for group in groups:
                standings.append(group)
        return standings

    # ------------------------------------------------------------------
    # Stats & Status
    # ------------------------------------------------------------------

    def get_request_count(self) -> int:
        """Get total API requests made this session."""
        return self.stats["requests_today"]

    def check_coverage(self) -> Optional[dict]:
        """Check what data types are available for World Cup 2026."""
        data = self._request("/leagues", {"id": WORLD_CUP_LEAGUE_ID})
        if data and "response" in data and data["response"]:
            return data["response"][0].get("coverage")
        return None

    def test_connection(self) -> bool:
        """Test if API key works by fetching a simple endpoint."""
        data = self._request("/status")
        if data and data.get("response"):
            print(f"  [API] Connection OK — {data['response'].get('requests', {}).get('current', 0)} requests used")
            return True
        return False


# ============================================================================
# Singleton
# ============================================================================

_api_client_instance = None


def get_api_client(api_key: str = None) -> ApiFootballClient:
    """Get or create the singleton API client."""
    global _api_client_instance
    if _api_client_instance is None:
        _api_client_instance = ApiFootballClient(api_key)
    elif api_key:
        _api_client_instance.set_key(api_key)
    return _api_client_instance


# ============================================================================
# Quick test
# ============================================================================

if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else None
    client = get_api_client(key)
    if client.is_configured():
        client.test_connection()
        print(f"  Teams: {len(client.get_teams())}")
        print(f"  Standings: {len(client.get_standings())}")
    else:
        print("No API key provided. Usage: python api_client.py YOUR_API_KEY")
