"""
Dynamic Data Manager
====================
Manages match results and updates team parameters in real-time.
After each match:
  - Elo ratings are updated
  - Recent form is recalculated
  - Team morale is adjusted

Data persisted to JSON files for continuity.
"""
import json
import math
import time
import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from .poisson_model import TeamStrength, EloRating, MatchStage
from .team_data import WORLD_CUP_TEAMS_2026


class DataManager:
    """
    Manages dynamic team data updates based on match results.

    Features:
    - Elo rating updates after each match
    - Recent form tracking (last 5 matches)
    - Morale adjustment based on results/streaks
    - Persistence to JSON files
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'web_app', 'data')
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.matches_file = os.path.join(data_dir, 'match_history.json')
        self.state_file = os.path.join(data_dir, 'team_state.json')

        # Initialize Elo system with current ratings
        self.elo = EloRating(k_factor=32)
        self._init_elo()

        # Recent form tracking (last N matches)
        self.form_history: Dict[str, deque] = {}
        self.max_form_matches = 5

        # Current dynamic state: {team_name: {form, morale, elo}}
        self.team_state: Dict[str, dict] = {}
        self.match_history: List[dict] = []

        # Load saved state
        self._load_state()

    def _init_elo(self):
        """Initialize Elo ratings from current team data."""
        for name, team in WORLD_CUP_TEAMS_2026.items():
            self.elo.set_rating(name, team.elo_rating)

    def _load_state(self):
        """Load saved state from JSON files."""
        # Load match history
        if os.path.exists(self.matches_file):
            try:
                with open(self.matches_file) as f:
                    self.match_history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.match_history = []

        # Load team state
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    saved = json.load(f)
                    for name, state in saved.items():
                        # Apply saved form/morale
                        if name in self.team_state:
                            self.team_state[name].update(state)
                        else:
                            self.team_state[name] = dict(state)
                        # Restore Elo
                        if 'elo' in state:
                            self.elo.set_rating(name, state['elo'])
            except (json.JSONDecodeError, IOError):
                pass

        # Ensure all teams have state initialized
        for name, team in WORLD_CUP_TEAMS_2026.items():
            if name not in self.team_state:
                self.team_state[name] = {
                    'form': team.recent_form,
                    'morale': team.morale,
                    'elo': team.elo_rating,
                }
            # Rebuild form history from match history
            if name not in self.form_history:
                self.form_history[name] = deque(maxlen=self.max_form_matches)

        # Rebuild form history from match history
        self._rebuild_form_history()

    def _rebuild_form_history(self):
        """Rebuild form history deque from saved match history."""
        self.form_history = {}
        for name in WORLD_CUP_TEAMS_2026:
            self.form_history[name] = deque(maxlen=self.max_form_matches)

        for match in self.match_history:
            home = match.get('home')
            away = match.get('away')
            hg = match.get('home_goals', 0)
            ag = match.get('away_goals', 0)
            if home in self.form_history:
                if hg > ag:
                    self.form_history[home].append('W')
                elif hg == ag:
                    self.form_history[home].append('D')
                else:
                    self.form_history[home].append('L')
            if away in self.form_history:
                if ag > hg:
                    self.form_history[away].append('W')
                elif ag == hg:
                    self.form_history[away].append('D')
                else:
                    self.form_history[away].append('L')

    def _save_state(self):
        """Save current state to JSON files."""
        # Save match history
        try:
            with open(self.matches_file, 'w') as f:
                json.dump(self.match_history[-500:], f, indent=2)  # Keep last 500
        except IOError:
            pass

        # Save team state
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.team_state, f, indent=2)
        except IOError:
            pass

    def add_match_result(
        self, home_team: str, away_team: str,
        home_goals: int, away_goals: int,
        stage: str = "group"
    ):
        """
        Record a match result and update all parameters.

        Updates:
        1. Match history
        2. Elo ratings
        3. Recent form
        4. Team morale
        """
        # Validate teams exist
        if home_team not in WORLD_CUP_TEAMS_2026 or away_team not in WORLD_CUP_TEAMS_2026:
            raise ValueError(f"Unknown team: {home_team} or {away_team}")

        # 1. Add to match history
        match_record = {
            'home': home_team,
            'away': away_team,
            'home_goals': home_goals,
            'away_goals': away_goals,
            'stage': stage,
            'timestamp': time.time(),
        }
        self.match_history.append(match_record)

        # 2. Update Elo ratings
        self.elo.update(home_team, away_team, home_goals, away_goals, margin_factor=1.2)

        # 3. Update form history
        if home_team not in self.form_history:
            self.form_history[home_team] = deque(maxlen=self.max_form_matches)
        if away_team not in self.form_history:
            self.form_history[away_team] = deque(maxlen=self.max_form_matches)

        if home_goals > away_goals:
            self.form_history[home_team].append('W')
            self.form_history[away_team].append('L')
        elif home_goals == away_goals:
            self.form_history[home_team].append('D')
            self.form_history[away_team].append('D')
        else:
            self.form_history[home_team].append('L')
            self.form_history[away_team].append('W')

        # 4. Update team state
        for team_name in [home_team, away_team]:
            if team_name not in self.team_state:
                orig = WORLD_CUP_TEAMS_2026[team_name]
                self.team_state[team_name] = {
                    'form': orig.recent_form,
                    'morale': orig.morale,
                    'elo': orig.elo_rating,
                }

            # Update Elo
            self.team_state[team_name]['elo'] = self.elo.get_rating(team_name)

            # Recalculate form from recent results
            self.team_state[team_name]['form'] = self._calculate_form(team_name)

            # Recalculate morale
            self.team_state[team_name]['morale'] = self._calculate_morale(team_name)

        # Save state
        self._save_state()

    def _calculate_form(self, team_name: str) -> float:
        """Calculate recent form (0.80-1.20) from last N matches."""
        history = list(self.form_history.get(team_name, []))
        if not history:
            orig = WORLD_CUP_TEAMS_2026[team_name]
            return orig.recent_form

        # Weight: more recent matches count more
        score = 1.0
        weights = [0.5, 0.3, 0.15, 0.05, 0.0]  # Last match matters most
        for i, result in enumerate(reversed(history)):
            w = weights[i] if i < len(weights) else 0.0
            if result == 'W':
                score += 0.08 * w
            elif result == 'D':
                score += 0.02 * w
            else:  # Loss
                score -= 0.06 * w

        return max(0.80, min(1.20, round(score, 3)))

    def _calculate_morale(self, team_name: str) -> float:
        """Calculate morale based on recent streak (0.80-1.20)."""
        history = list(self.form_history.get(team_name, []))
        orig = WORLD_CUP_TEAMS_2026[team_name]
        morale = orig.morale

        if len(history) < 2:
            return morale

        # Check recent streak
        recent = history[-3:]  # Last 3 matches
        wins = recent.count('W')
        losses = recent.count('L')

        if wins == 3:
            morale = min(1.20, orig.morale + 0.12)
        elif wins == 2:
            morale = min(1.15, orig.morale + 0.06)
        elif losses >= 2:
            morale = max(0.85, orig.morale - 0.08)
        elif losses == 3:
            morale = max(0.80, orig.morale - 0.15)

        return round(morale, 3)

    def get_dynamic_team(self, team_name: str, use_player_data: bool = False) -> TeamStrength:
        """
        Get team with dynamically updated parameters.
        Returns a TeamStrength with current Elo, form, and morale.

        Args:
            team_name: Name of the team
            use_player_data: If True, blend in player-derived strength (attack/defense)
                            Requires TeamIntegrator to be initialized.
        """
        base = WORLD_CUP_TEAMS_2026.get(team_name)
        if not base:
            return TeamStrength(name=team_name, attack=1.0, defense=1.0,
                               recent_form=1.0, morale=1.0)

        state = self.team_state.get(team_name, {})
        form = state.get('form', base.recent_form)
        morale = state.get('morale', base.morale)
        elo = state.get('elo', base.elo_rating)

        # If player data integration is enabled, get blended params
        attack = base.attack
        defense = base.defense
        injury_factor = base.injury_factor

        if use_player_data:
            try:
                from .team_integrator import get_team_integrator
                integrator = get_team_integrator(self)
                blended = integrator.get_blended_team_strength(team_name)
                attack = blended.attack
                defense = blended.defense
                injury_factor = blended.injury_factor
            except ImportError:
                pass

        return TeamStrength(
            name=base.name,
            fifa_ranking=base.fifa_ranking,
            attack=attack,
            defense=defense,
            elo_rating=elo,
            recent_form=form,
            morale=morale,
            injury_factor=injury_factor,
            group=base.group,
            squad_value=base.squad_value,
            host_factor=base.host_factor,
        )

    def get_match_history(self, limit: int = 50) -> List[dict]:
        """Get recent match history."""
        return self.match_history[-limit:]

    def get_team_summary(self, team_name: str) -> dict:
        """Get summary of a team's current state."""
        state = self.team_state.get(team_name, {})
        base = WORLD_CUP_TEAMS_2026.get(team_name)
        if not base:
            return {}
        return {
            'name': team_name,
            'fifa_ranking': base.fifa_ranking,
            'attack': base.attack,
            'defense': base.defense,
            'current_elo': state.get('elo', base.elo_rating),
            'base_elo': base.elo_rating,
            'current_form': state.get('form', base.recent_form),
            'base_form': base.recent_form,
            'current_morale': state.get('morale', base.morale),
            'base_morale': base.morale,
            'recent_results': list(self.form_history.get(team_name, [])),
        }


# Singleton instance for web app use
_data_manager_instance = None


def get_data_manager(data_dir: str = None) -> DataManager:
    """Get or create the singleton DataManager."""
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager(data_dir)
    return _data_manager_instance


def reset_data_manager():
    """Reset the singleton (for testing)."""
    global _data_manager_instance
    _data_manager_instance = None
