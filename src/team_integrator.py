"""
Team Strength Integrator
==========================
Bridges player-level data into the Poisson prediction model.

Flow:
  1. PlayerStateCalculator computes individual player states
  2. TeamStrengthAggregator aggregates to team-level coefficients
  3. Blends with base TeamStrength params from team_data.py
  4. DataManager.get_dynamic_team() returns the blended result

Usage in web_app/server.py:
  from src.team_integrator import get_team_integrator
  integrator = get_team_integrator(data_manager)
  integrator.refresh_all()  # Called periodically (scheduler)
  strength = integrator.get_blended_team("Brazil")  # => TeamStrength
"""
import json
import os
import time
from typing import Dict, List, Optional, Tuple
from .poisson_model import TeamStrength
from .team_data import WORLD_CUP_TEAMS_2026
from .player_state import (
    PlayerRecord,
    PlayerStateCalculator,
    TeamStrengthAggregator,
    apply_team_strength_to_prediction,
    get_league_quality,
)


SQUADS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'teams', 'world_cup_squads.json')
PLAYER_STATE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'players_state.json')
TEAM_STRENGTH_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'team_strength.json')


class TeamIntegrator:
    """Integrates player-level data into team strength calculations.

    Coordinates between:
      - Squad database (world_cup_squads.json)
      - Player state calculator
      - Team strength aggregator
      - Base team data (team_data.py)
    """

    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self.calculator = PlayerStateCalculator()
        self.aggregator = TeamStrengthAggregator()

        # Data caches
        self.squad_data: Dict[str, List[PlayerRecord]] = {}   # team_name -> players
        self.team_strength_cache: Dict[str, dict] = {}         # team_name -> strength result
        self.blended_params: Dict[str, dict] = {}              # team_name -> {attack, defense}

        # Stats
        self.last_refresh = 0.0
        self.refresh_count = 0

        # Load saved data
        self._load_data()

    # ------------------------------------------------------------------
    # Data Persistence
    # ------------------------------------------------------------------

    def _load_data(self):
        """Load saved player state and team strength data."""
        # Load squad data
        if os.path.exists(SQUADS_PATH):
            try:
                with open(SQUADS_PATH) as f:
                    raw = json.load(f)
                for team_name, players_raw in raw.get("squads", {}).items():
                    self.squad_data[team_name] = [
                        PlayerRecord.from_dict(p) if isinstance(p, dict)
                        else self._dict_to_player(p, team_name)
                        for p in players_raw
                    ]
                print(f"  [Integrator] Loaded {len(self.squad_data)} team squads")
            except Exception as e:
                print(f"  [Integrator] Error loading squads: {e}")

        # Load computed player state
        if os.path.exists(PLAYER_STATE_PATH):
            try:
                with open(PLAYER_STATE_PATH) as f:
                    saved_players = json.load(f)
                for team_name, players_list in saved_players.items():
                    if team_name not in self.squad_data:
                        self.squad_data[team_name] = []
                    existing = {p.player_id for p in self.squad_data[team_name]}
                    for pd in players_list:
                        if pd.get("player_id") not in existing:
                            self.squad_data[team_name].append(PlayerRecord.from_dict(pd))
                print(f"  [Integrator] Loaded player states for {len(saved_players)} teams")
            except Exception as e:
                print(f"  [Integrator] Error loading player states: {e}")

        # Load computed team strength
        if os.path.exists(TEAM_STRENGTH_PATH):
            try:
                with open(TEAM_STRENGTH_PATH) as f:
                    self.team_strength_cache = json.load(f)
                print(f"  [Integrator] Loaded team strength for {len(self.team_strength_cache)} teams")
            except Exception as e:
                print(f"  [Integrator] Error loading team strength: {e}")

    def _save_player_states(self):
        """Save all player states to JSON."""
        data = {}
        for team_name, players in self.squad_data.items():
            data[team_name] = [p.to_dict() for p in players]
        try:
            os.makedirs(os.path.dirname(PLAYER_STATE_PATH), exist_ok=True)
            with open(PLAYER_STATE_PATH, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [Integrator] Error saving player states: {e}")

    def _save_team_strength(self):
        """Save computed team strengths to JSON."""
        try:
            os.makedirs(os.path.dirname(TEAM_STRENGTH_PATH), exist_ok=True)
            with open(TEAM_STRENGTH_PATH, 'w') as f:
                json.dump(self.team_strength_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [Integrator] Error saving team strength: {e}")

    # ------------------------------------------------------------------
    # Player Management
    # ------------------------------------------------------------------

    def get_players(self, team_name: str) -> List[PlayerRecord]:
        """Get player records for a team."""
        return self.squad_data.get(team_name, [])

    def set_squad(self, team_name: str, players: List[PlayerRecord]):
        """Set/replace the squad for a team."""
        self.squad_data[team_name] = players

    def update_player_match_data(self, team_name: str, player_id: int, match_data: dict):
        """Update a player's recent match data from API."""
        players = self.squad_data.get(team_name, [])
        for p in players:
            if p.player_id == player_id:
                p.recent_matches.append(match_data)
                if len(p.recent_matches) > 10:
                    p.recent_matches = p.recent_matches[-10:]
                break

    def update_player_injury(self, team_name: str, player_id: int, is_injured: bool, details: str = ""):
        """Update injury status for a player."""
        players = self.squad_data.get(team_name, [])
        for p in players:
            if p.player_id == player_id:
                p.is_injured = is_injured
                p.injury_details = details
                break

    # ------------------------------------------------------------------
    # Core Refresh
    # ------------------------------------------------------------------

    def refresh_all(self):
        """Refresh all computations: player states → team strengths → blended params."""
        print(f"  [Integrator] Refreshing all team strengths...")
        self.refresh_count += 1

        # 1. Compute player states
        for team_name, players in self.squad_data.items():
            for p in players:
                self.calculator.compute_state(p)

        # 2. Compute team strengths from players
        self.team_strength_cache = {}
        for team_name, players in self.squad_data.items():
            if players:
                strength = self.aggregator.compute_team_strength(team_name, players)
                self.team_strength_cache[team_name] = strength

        # 3. Blend with base params
        self._compute_blended_params()

        # 4. Save
        self._save_player_states()
        self._save_team_strength()
        self.last_refresh = time.time()

        teams_updated = len(self.team_strength_cache)
        players_updated = sum(len(v) for v in self.squad_data.values())
        print(f"  [Integrator] Refreshed {teams_updated} teams, {players_updated} players")

    def _compute_blended_params(self):
        """Blend player-derived strength with base team parameters."""
        self.blended_params = {}
        for team_name, base in WORLD_CUP_TEAMS_2026.items():
            strength = self.team_strength_cache.get(team_name)
            if strength:
                adj_attack, adj_defense = apply_team_strength_to_prediction(
                    base.attack, base.defense, strength, blend=0.35
                )
                self.blended_params[team_name] = {
                    "attack": adj_attack,
                    "defense": adj_defense,
                    "midfield": strength.get("midfield", 1.0),
                }
            else:
                self.blended_params[team_name] = {
                    "attack": base.attack,
                    "defense": base.defense,
                    "midfield": 1.0,
                }

    # ------------------------------------------------------------------
    # Data Access (used by DataManager)
    # ------------------------------------------------------------------

    def get_blended_team_strength(self, team_name: str) -> TeamStrength:
        """Get TeamStrength with blended player data.

        This is the main integration point — called by DataManager.get_dynamic_team().
        Falls back to base team data if no player data available.
        """
        base = WORLD_CUP_TEAMS_2026.get(team_name)
        if not base:
            return TeamStrength(name=team_name, attack=1.0, defense=1.0,
                               recent_form=1.0, morale=1.0)

        blended = self.blended_params.get(team_name, {})
        strength = self.team_strength_cache.get(team_name, {})

        # Get dynamic state from DataManager if available
        dynamic = {}
        if self.data_manager:
            state = self.data_manager.team_state.get(team_name, {})
            dynamic = state

        return TeamStrength(
            name=base.name,
            fifa_ranking=base.fifa_ranking,
            attack=blended.get("attack", base.attack),
            defense=blended.get("defense", base.defense),
            elo_rating=dynamic.get("elo", base.elo_rating),
            recent_form=dynamic.get("form", base.recent_form),
            morale=dynamic.get("morale", base.morale),
            injury_factor=max(0.7, 1.0 - strength.get("injured_count", 0) * 0.03),
            group=base.group,
            squad_value=base.squad_value,
            host_factor=base.host_factor,
        )

    def get_team_report(self, team_name: str) -> dict:
        """Get a detailed team report for the admin page."""
        base = WORLD_CUP_TEAMS_2026.get(team_name)
        strength = self.team_strength_cache.get(team_name, {})
        players = self.squad_data.get(team_name, [])

        injured = [p.to_dict() for p in players if p.is_injured]
        top_players = sorted(
            [p.to_dict() for p in players],
            key=lambda x: x["overall"],
            reverse=True,
        )[:11]

        return {
            "team": team_name,
            "fifa_ranking": base.fifa_ranking if base else 0,
            "base_attack": base.attack if base else 1.0,
            "base_defense": base.defense if base else 1.0,
            "player_adjusted_attack": strength.get("attack", 1.0),
            "player_adjusted_defense": strength.get("defense", 1.0),
            "overall": strength.get("overall", 1.0),
            "bench_depth": strength.get("bench_depth", 0),
            "league_quality": strength.get("league_quality_factor", 0.5),
            "injured_count": len(injured),
            "injured_players": injured,
            "predicted_xi": top_players[:11],
            "player_count": len(players),
        }

    def get_status(self) -> dict:
        """Get integrator status for the admin page."""
        hours_since = (time.time() - self.last_refresh) / 3600 if self.last_refresh else 999
        return {
            "teams_with_squads": len(self.squad_data),
            "total_players": sum(len(v) for v in self.squad_data.values()),
            "last_refresh": self.last_refresh,
            "hours_since_refresh": round(hours_since, 1),
            "refresh_count": self.refresh_count,
            "is_initialized": self.last_refresh > 0,
        }

    # ------------------------------------------------------------------
    # API Data Integration
    # ------------------------------------------------------------------

    def populate_from_api(self, api_client, teams_data: List[dict] = None):
        """Populate squad data from API-Football.

        Called by the scheduler every 4-6 hours.
        Requires a configured ApiFootballClient with valid key.

        Args:
            api_client: Configured ApiFootballClient instance
            teams_data: Optional pre-fetched team list (to save API calls)
        """
        if not api_client or not api_client.is_configured():
            print("  [Integrator] API not configured, skipping populate")
            return

        print("  [Integrator] Populating squad data from API...")

        # Get teams if not provided
        if not teams_data:
            teams_data = api_client.get_teams()

        for team in teams_data:
            team_info = team.get("team", {})
            team_name = team_info.get("name", "")
            team_id = team_info.get("id", 0)

            if not team_name:
                continue

            # Map API team name to our internal name
            internal_name = self._map_team_name(team_name)

            # Get squad
            squad = api_client.get_squad(team_id)
            if not squad:
                continue

            # Convert to PlayerRecords
            players = []
            for player in squad:
                pid = player.get("id", 0)
                name = player.get("name", "")
                pos = player.get("position", "")
                age = player.get("age", 25)
                nationality = player.get("nationality", "")

                # Check if we already have this player (preserve match data)
                existing = self._find_player(internal_name, pid) if internal_name else None
                if existing:
                    players.append(existing)
                else:
                    record = PlayerRecord(
                        player_id=pid,
                        name=name,
                        position=pos,
                        team_name=internal_name or team_name,
                        age=age,
                        nationality=nationality,
                    )
                    players.append(record)

            if internal_name and players:
                self.squad_data[internal_name] = players

        print(f"  [Integrator] Populated {len(self.squad_data)} teams from API")

    def fetch_and_apply_player_stats(self, api_client, fixture_id: int):
        """Fetch player ratings from a specific match and apply to records.

        Args:
            api_client: Configured ApiFootballClient
            fixture_id: API fixture ID
        """
        if not api_client or not api_client.is_configured():
            return

        data = api_client.get_fixture_player_stats(fixture_id)
        for team_data in data:
            team_info = team_data.get("team", {})
            team_name = self._map_team_name(team_info.get("name", ""))
            if not team_name:
                continue

            players_stats = team_data.get("players", [])
            for ps in players_stats:
                player_info = ps.get("player", {})
                stats = ps.get("statistics", [{}])[0] if ps.get("statistics") else {}

                pid = player_info.get("id", 0)
                player = self._find_player(team_name, pid)
                if not player:
                    continue

                # Extract stats
                games = stats.get("games", {})
                minutes = games.get("minutes", 0)
                rating_str = games.get("rating", "0")
                try:
                    rating = float(rating_str) if rating_str else 0.0
                except (ValueError, TypeError):
                    rating = 0.0

                goals = stats.get("goals", {}).get("total", 0)
                assists = stats.get("goals", {}).get("assists", 0)

                # Get fixture date from context if available
                match_data = {
                    "minutes": minutes,
                    "rating": rating,
                    "goals": goals,
                    "assists": assists,
                    "injured": False,
                }

                player.recent_matches.append(match_data)
                if len(player.recent_matches) > 10:
                    player.recent_matches = player.recent_matches[-10:]

    def _find_player(self, team_name: str, player_id: int) -> Optional[PlayerRecord]:
        """Find a player by ID in a team's squad."""
        players = self.squad_data.get(team_name, [])
        for p in players:
            if p.player_id == player_id:
                return p
        return None

    @staticmethod
    def _map_team_name(api_name: str) -> Optional[str]:
        """Map API-Football team name to internal team name."""
        mapping = {
            "Brazil": "Brazil",
            "Argentina": "Argentina",
            "France": "France",
            "England": "England",
            "Germany": "Germany",
            "Spain": "Spain",
            "Portugal": "Portugal",
            "Netherlands": "Netherlands",
            "Belgium": "Belgium",
            "Croatia": "Croatia",
            "Italy": "Italy",
            "Uruguay": "Uruguay",
            "Japan": "Japan",
            "South Korea": "South Korea",
            "Korea Republic": "South Korea",
            "USA": "USA",
            "United States": "USA",
            "Mexico": "Mexico",
            "Canada": "Canada",
            "Morocco": "Morocco",
            "Senegal": "Senegal",
            "Nigeria": "Nigeria",
            "Cameroon": "Cameroon",
            "Ghana": "Ghana",
            "Tunisia": "Tunisia",
            "Egypt": "Egypt",
            "Australia": "Australia",
            "Saudi Arabia": "Saudi Arabia",
            "Iran": "Iran",
            "Ecuador": "Ecuador",
            "Peru": "Peru",
            "Chile": "Chile",
            "Colombia": "Colombia",
            "Paraguay": "Paraguay",
            "Switzerland": "Switzerland",
            "Denmark": "Denmark",
            "Poland": "Poland",
            "Sweden": "Sweden",
            "Norway": "Norway",
            "Ukraine": "Ukraine",
            "Serbia": "Serbia",
            "Turkey": "Turkey",
            "Czech Republic": "Czech Republic",
            "Hungary": "Hungary",
            "Austria": "Austria",
            "Wales": "Wales",
            "Scotland": "Scotland",
            "Russia": "Russia",
            "Algeria": "Algeria",
            "Ivory Coast": "Ivory Coast",
            "Cote d'Ivoire": "Ivory Coast",
            "Mali": "Mali",
            "Burkina Faso": "Burkina Faso",
            "South Africa": "South Africa",
            "DR Congo": "DR Congo",
            "Congo DR": "DR Congo",
            "Costa Rica": "Costa Rica",
            "Panama": "Panama",
            "Honduras": "Honduras",
            "Jamaica": "Jamaica",
            "New Zealand": "New Zealand",
            "Iraq": "Iraq",
            "United Arab Emirates": "UAE",
            "UAE": "UAE",
            "Qatar": "Qatar",
            "Oman": "Oman",
            "Uzbekistan": "Uzbekistan",
            "China": "China",
            "Indonesia": "Indonesia",
        }
        return mapping.get(api_name)


# ============================================================================
# Singleton
# ============================================================================

_integrator_instance = None


def get_team_integrator(data_manager=None) -> TeamIntegrator:
    """Get or create the singleton TeamIntegrator."""
    global _integrator_instance
    if _integrator_instance is None:
        _integrator_instance = TeamIntegrator(data_manager)
    elif data_manager:
        _integrator_instance.data_manager = data_manager
    return _integrator_instance


def reset_integrator():
    """Reset the singleton (for testing)."""
    global _integrator_instance
    _integrator_instance = None
