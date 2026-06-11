"""
Player State & Team Strength System
======================================
Calculates individual player state (0-100) from API data,
then aggregates to team-level fighting strength.

Three dimensions for player state:
  1. Recent form (60%):  rating, minutes, goals/assists, days since last match
  2. Fitness (20%):      injury status, injury frequency, fatigue
  3. Experience (20%):   national caps, tournament experience

Team strength aggregates from predicted starting XI + bench depth.
"""
import json
import math
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


# ============================================================================
# League Quality Coefficients
# ============================================================================
# Scale: 0.0-1.0 — how well league form translates to World Cup performance

LEAGUE_QUALITY: Dict[str, float] = {
    # Top 5 European
    "Premier League":      1.00,
    "English Premier League": 1.00,
    "Premier League (ENG)": 1.00,
    "La Liga":             0.95,
    "La Liga (ESP)":       0.95,
    "Bundesliga":          0.95,
    "Bundesliga (GER)":    0.95,
    "Serie A":             0.90,
    "Serie A (ITA)":       0.90,
    "Ligue 1":             0.88,
    "Ligue 1 (FRA)":       0.88,
    # Other European
    "Primeira Liga":       0.80,
    "Eredivisie":          0.78,
    "Belgian Pro League":  0.72,
    "Super Lig":           0.65,
    "Russian Premier Liga": 0.65,
    "Ukrainian Premier League": 0.60,
    "Championship":        0.75,
    "Scottish Premiership": 0.68,
    "Swiss Super League":  0.62,
    "Austrian Bundesliga": 0.60,
    "Czech First League":  0.55,
    "Greek Super League":  0.58,
    "Croatian HNL":        0.52,
    "Danish Superliga":    0.55,
    # Americas
    "MLS":                 0.60,
    "Brazilian Serie A":   0.58,
    "Argentine Primera":   0.55,
    "Liga MX":             0.55,
    "Colombian Primera A": 0.48,
    "Chilean Primera":     0.45,
    # Asia
    "J1 League":           0.52,
    "K League 1":          0.50,
    "Saudi Pro League":    0.48,
    "Qatar Stars League":  0.42,
    "UAE Pro League":      0.40,
    "Chinese Super League": 0.45,
    "A-League":            0.42,
    # Africa
    "Egyptian Premier League": 0.40,
    "South African Premier": 0.38,
    "Moroccan Botola":     0.35,
    "Tunisian Ligue":      0.33,
    # Unknown / other
    "":                    0.40,
}

DEFAULT_LEAGUE_QUALITY = 0.40


def get_league_quality(league_name: str) -> float:
    """Get quality coefficient for a league."""
    return LEAGUE_QUALITY.get(league_name, DEFAULT_LEAGUE_QUALITY)


# ============================================================================
# Position Weights (how much each position contributes to team strength)
# ============================================================================

POSITION_WEIGHTS = {
    "Goalkeeper": 0.15,
    "Defender": 0.25,
    "Midfielder": 0.30,
    "Forward": 0.30,
}

POSITION_CATEGORIES = {
    "Goalkeeper": ["Goalkeeper", "Keeper", "GK"],
    "Defender": ["Defender", "Centre-Back", "Right-Back", "Left-Back", "CB", "RB", "LB"],
    "Midfielder": ["Midfielder", "Attacking Midfield", "Central Midfield", "Defensive Midfield",
                   "Right Midfield", "Left Midfield", "CM", "CDM", "CAM", "RM", "LM"],
    "Forward": ["Forward", "Attacker", "Centre-Forward", "Striker", "Winger",
                "Right Winger", "Left Winger", "CF", "RW", "LW", "SS"],
}


def classify_position(api_position: str) -> str:
    """Classify an API position string into a category."""
    if not api_position:
        return "Midfielder"
    api_pos = api_position.strip().lower()
    for category, keywords in POSITION_CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in api_pos:
                return category
    return "Midfielder"


# ============================================================================
# Player Record
# ============================================================================

class PlayerRecord:
    """A single player's record - persists across API updates."""

    def __init__(
        self,
        player_id: int,
        name: str,
        position: str,
        team_name: str,       # National team
        club_name: str = "",
        club_team_id: int = 0,
        league_name: str = "",
        age: int = 25,
        nationality: str = "",
    ):
        self.player_id = player_id
        self.name = name
        self.position = classify_position(position)
        self.position_raw = position
        self.team_name = team_name          # National team
        self.club_name = club_name
        self.club_team_id = club_team_id
        self.league_name = league_name
        self.age = age
        self.nationality = nationality
        self.caps = 0                       # National team appearances
        self.is_injured = False
        self.injury_details = ""

        # Recent match data (last 5 matches)
        self.recent_matches: List[dict] = []

        # Computed state (0-100)
        self.form_score = 50.0
        self.fitness_score = 50.0
        self.experience_score = 50.0
        self.overall = 50.0

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position,
            "position_raw": self.position_raw,
            "team_name": self.team_name,
            "club_name": self.club_name,
            "club_team_id": self.club_team_id,
            "league_name": self.league_name,
            "age": self.age,
            "nationality": self.nationality,
            "caps": self.caps,
            "is_injured": self.is_injured,
            "injury_details": self.injury_details,
            "form_score": round(self.form_score, 1),
            "fitness_score": round(self.fitness_score, 1),
            "experience_score": round(self.experience_score, 1),
            "overall": round(self.overall, 1),
            "recent_matches": self.recent_matches[-5:],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerRecord":
        p = cls(
            player_id=data["player_id"],
            name=data["name"],
            position=data.get("position_raw", data.get("position", "")),
            team_name=data.get("team_name", ""),
            club_name=data.get("club_name", ""),
            club_team_id=data.get("club_team_id", 0),
            league_name=data.get("league_name", ""),
            age=data.get("age", 25),
            nationality=data.get("nationality", ""),
        )
        p.caps = data.get("caps", 0)
        p.is_injured = data.get("is_injured", False)
        p.injury_details = data.get("injury_details", "")
        p.form_score = data.get("form_score", 50.0)
        p.fitness_score = data.get("fitness_score", 50.0)
        p.experience_score = data.get("experience_score", 50.0)
        p.overall = data.get("overall", 50.0)
        p.recent_matches = data.get("recent_matches", [])
        return p


# ============================================================================
# Player State Calculator
# ============================================================================

class PlayerStateCalculator:
    """Compute player state from raw API data."""

    def compute_state(self, player: PlayerRecord) -> PlayerRecord:
        """Recompute all three dimensions of player state."""
        self._compute_form(player)
        self._compute_fitness(player)
        self._compute_experience(player)
        # Overall = weighted sum
        player.overall = (
            player.form_score * 0.60 +
            player.fitness_score * 0.20 +
            player.experience_score * 0.20
        )
        return player

    def _compute_form(self, player: PlayerRecord):
        """Recent form (0-100) from last 5 matches."""
        matches = player.recent_matches[-5:]
        if not matches:
            player.form_score = 40.0  # No data = moderate-low
            return

        # Average rating (API ratings are 0-10)
        ratings = [m.get("rating", 0) for m in matches if m.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 6.0

        # Minutes played trend
        minutes = [m.get("minutes", 0) for m in matches]
        avg_minutes = sum(minutes) / len(minutes) if minutes else 0

        # Goals + assists contribution
        goals = sum(m.get("goals", 0) for m in matches)
        assists = sum(m.get("assists", 0) for m in matches)

        # Days since last match (penalty for long gaps)
        days_since = 999
        if matches and matches[-1].get("date"):
            try:
                last_date = datetime.strptime(matches[-1]["date"], "%Y-%m-%d")
                days_since = (datetime.now() - last_date).days
            except (ValueError, TypeError):
                pass

        # Score calculation
        rating_score = min(avg_rating * 10, 90)  # rating 7.0 → 70
        minutes_score = min(avg_minutes / 90 * 100, 100)  # 90 min → 100
        contribution_score = min((goals * 10 + assists * 5), 100)
        gap_penalty = min(days_since * 2, 30)  # 15 days → -30

        player.form_score = max(10, min(100,
            rating_score * 0.40 +
            minutes_score * 0.30 +
            contribution_score * 0.15 -
            gap_penalty * 0.15
        ))

    def _compute_fitness(self, player: PlayerRecord):
        """Fitness (0-100) from injury and fatigue data."""
        if player.is_injured:
            player.fitness_score = 5.0
            return

        # Injury frequency penalty
        matches = player.recent_matches[-10:]
        injury_events = sum(1 for m in matches if m.get("injured", False))
        freq_penalty = min(injury_events * 10, 30)

        # Fatigue from match density
        if len(matches) >= 4:
            recent_days = 30
            fatigue = min(len(matches) / recent_days * 100, 30)
        else:
            fatigue = 0

        player.fitness_score = max(10, min(100, 100 - freq_penalty - fatigue))

    def _compute_experience(self, player: PlayerRecord):
        """Experience (0-100) from caps and tournament history."""
        caps_score = min(player.caps / 1.5, 60)  # 90 caps → 60
        age_score = min(max((player.age - 18) * 3, 10), 30)  # 18→10, 30→36, cap at 30
        player.experience_score = min(100, caps_score + age_score + 10)


# ============================================================================
# Team Strength Aggregator
# ============================================================================

class TeamStrengthAggregator:
    """Aggregate player states into team-level fighting strength.

    Produces the final team parameters used by the Poisson prediction model.
    """

    def __init__(self):
        self.calculator = PlayerStateCalculator()

    def compute_team_strength(
        self,
        team_name: str,
        players: List[PlayerRecord],
    ) -> dict:
        """Compute team fighting strength from its players.

        Returns:
            dict with: attack, defense, midfield, overall,
                       bench_depth, league_quality_factor, key_players
        """
        if not players:
            return {
                "team": team_name,
                "attack": 1.0,
                "defense": 1.0,
                "midfield": 1.0,
                "overall": 1.0,
                "bench_depth": 1.0,
                "league_quality_factor": 1.0,
                "key_players": [],
                "injured_count": 0,
            }

        # Compute states for all players
        for p in players:
            self.calculator.compute_state(p)

        # Sort by overall score (highest first = predicted starters)
        sorted_players = sorted(players, key=lambda p: p.overall, reverse=True)

        # Predicted starting XI (top players weighted by position)
        starters = self._select_starting_xi(sorted_players)
        bench = sorted_players[len(starters):]

        # Calculate position-specific scores from starters
        attack_score = self._position_score(starters, "Forward")
        midfield_score = self._position_score(starters, "Midfielder")
        defense_score = self._position_score(starters, "Defender")
        gk_score = self._position_score(starters, "Goalkeeper")

        # League quality: average of starting XI's league coefficients
        league_factor = self._league_quality_factor(starters)

        # Bench depth: how much quality drops from starters to bench
        bench_depth = self._bench_depth(starters, bench)

        # Injured count
        injured = sum(1 for p in players if p.is_injured)

        # Normalize to expected range (0.5-2.0)
        # Starting from base 1.0, adjusted by player quality
        base = 1.0
        attack = base + (attack_score - 50) * 0.012
        midfield = base + (midfield_score - 50) * 0.012
        defense = base + (defense_score - 50) * 0.012
        gk_adj = (gk_score - 50) * 0.006
        defense += gk_adj

        # Apply league quality factor
        attack *= 0.7 + 0.3 * league_factor
        midfield *= 0.7 + 0.3 * league_factor
        defense *= 0.7 + 0.3 * league_factor

        # Apply bench depth (broader bench = better)
        depth_factor = 0.9 + 0.1 * min(bench_depth / 10, 1.0)
        attack *= depth_factor
        midfield *= depth_factor
        defense *= depth_factor

        # Injury penalty
        injury_penalty = max(0.85, 1.0 - injured * 0.02)
        attack *= injury_penalty
        midfield *= injury_penalty
        defense *= injury_penalty

        # Clamp to reasonable range
        attack = max(0.5, min(2.0, attack))
        midfield = max(0.5, min(2.0, midfield))
        defense = max(0.5, min(2.0, defense))
        overall = (attack * 0.35 + midfield * 0.35 + defense * 0.30)

        # Key players (top 5 by overall)
        key_players = [
            {"name": p.name, "position": p.position, "overall": round(p.overall, 1)}
            for p in sorted_players[:5]
        ]

        return {
            "team": team_name,
            "attack": round(attack, 4),
            "defense": round(defense, 4),
            "midfield": round(midfield, 4),
            "overall": round(overall, 4),
            "bench_depth": round(bench_depth, 1),
            "league_quality_factor": round(league_factor, 3),
            "key_players": key_players,
            "injured_count": injured,
        }

    def _select_starting_xi(self, sorted_players: List[PlayerRecord]) -> List[PlayerRecord]:
        """Select predicted starting XI with position balance."""
        # Ensure at least 1 GK, 4 DEF, 4 MID, 2 FWD minimum coverage
        gk = [p for p in sorted_players if p.position == "Goalkeeper"]
        defs = [p for p in sorted_players if p.position == "Defender"]
        mids = [p for p in sorted_players if p.position == "Midfielder"]
        fwds = [p for p in sorted_players if p.position == "Forward"]

        starters = []
        used_ids = set()

        # Must have 1 GK
        for p in gk[:1]:
            starters.append(p)
            used_ids.add(p.player_id)

        # Pick top defenders (up to 4)
        for p in defs[:4]:
            if p.player_id not in used_ids:
                starters.append(p)
                used_ids.add(p.player_id)

        # Pick top midfielders (up to 4)
        for p in mids[:4]:
            if p.player_id not in used_ids:
                starters.append(p)
                used_ids.add(p.player_id)

        # Pick top forwards (up to 2)
        for p in fwds[:2]:
            if p.player_id not in used_ids:
                starters.append(p)
                used_ids.add(p.player_id)

        # Fill remaining slots with best available
        remaining = 11 - len(starters)
        if remaining > 0:
            for p in sorted_players:
                if p.player_id not in used_ids and remaining > 0:
                    starters.append(p)
                    used_ids.add(p.player_id)
                    remaining -= 1

        return starters

    def _position_score(self, players: List[PlayerRecord], position: str) -> float:
        """Average overall score for a position group."""
        pos_players = [p for p in players if p.position == position]
        if not pos_players:
            return 50.0
        return sum(p.overall for p in pos_players) / len(pos_players)

    def _league_quality_factor(self, players: List[PlayerRecord]) -> float:
        """Average league quality for a group of players."""
        if not players:
            return 0.5
        scores = [get_league_quality(p.league_name) for p in players]
        return sum(scores) / len(scores)

    def _bench_depth(self, starters: List[PlayerRecord], bench: List[PlayerRecord]) -> float:
        """Compute bench depth score.

        Higher = better bench (small quality gap between starters and subs).
        Returns a depth score (0-100).
        """
        if not bench:
            return 0
        starter_avg = sum(p.overall for p in starters) / len(starters) if starters else 50
        bench_avg = sum(p.overall for p in bench) / len(bench) if bench else 0

        gap = starter_avg - bench_avg
        # Smaller gap = better depth. Score 0-100.
        depth = max(0, 100 - gap * 2)
        return depth


# ============================================================================
# Main API for external use
# ============================================================================

def compute_team_strength_from_squad(team_name: str, players: List[PlayerRecord]) -> dict:
    """Convenience: compute team strength from a list of PlayerRecords."""
    aggregator = TeamStrengthAggregator()
    return aggregator.compute_team_strength(team_name, players)


def apply_team_strength_to_prediction(
    base_attack: float,
    base_defense: float,
    strength_result: dict,
    blend: float = 0.35,
) -> Tuple[float, float]:
    """Blend base team parameters with player-derived strength.

    Args:
        base_attack: Original attack coefficient (e.g. from team_data.py)
        base_defense: Original defense coefficient
        strength_result: Output from compute_team_strength()
        blend: How much weight to give player data (0.0 = pure base, 1.0 = pure player)

    Returns:
        (adjusted_attack, adjusted_defense)
    """
    player_attack = strength_result.get("attack", 1.0)
    player_defense = strength_result.get("defense", 1.0)

    adjusted_attack = base_attack * (1 - blend) + base_attack * player_attack * blend
    adjusted_defense = base_defense * (1 - blend) + base_defense * player_defense * blend

    return adjusted_attack, adjusted_defense
