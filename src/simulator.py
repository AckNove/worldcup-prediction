"""
2026 World Cup Dynamic Tournament Simulator
=============================================
Full dynamic simulation: group stage -> R32 -> R16 -> QF -> SF -> Final
Uses real 2026 FIFA bracket format with Monte Carlo runs for champion odds.
"""
import random
import math
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from .poisson_model import PoissonPredictor, TeamStrength, MatchStage
from .team_data import WORLD_CUP_TEAMS_2026, GROUP_STAGE_MATCHUPS, GROUP_MEMBERS


class WorldCupSimulator:
    """Full 2026 World Cup tournament simulator with dynamic bracket."""

    def __init__(self, n_simulations: int = 10000):
        self.predictor = PoissonPredictor(home_advantage=1.05)
        self.n_simulations = n_simulations

    def simulate_match(
        self, home: TeamStrength, away: TeamStrength,
        stage: MatchStage = MatchStage.GROUP
    ) -> Tuple[int, int]:
        """Simulate one match, return (home_goals, away_goals)."""
        lambda_home, lambda_away = self.predictor.expected_goals(home, away, stage)
        return (
            self._poisson_variate(lambda_home),
            self._poisson_variate(lambda_away)
        )

    @staticmethod
    def _poisson_variate(lambda_: float) -> int:
        """Generate Poisson random variate (works on all Python 3.x)."""
        if lambda_ <= 0:
            return 0
        L = math.exp(-lambda_)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1

    # =========================================================================
    # Group Stage
    # =========================================================================

    def _simulate_group_stage(self, teams: Dict[str, TeamStrength]) -> Dict:
        """Simulate all 72 group matches. Returns detailed group standings."""
        group_standings = {}

        for group, members in GROUP_MEMBERS.items():
            standing = {}
            for name in members:
                standing[name] = {"pts": 0, "gd": 0, "gf": 0, "ga": 0}
            group_standings[group] = standing

            group_matches = [(h, a) for (h, a, r) in GROUP_STAGE_MATCHUPS
                            if h in members or a in members]

            for home_name, away_name in group_matches:
                home = teams[home_name]
                away = teams[away_name]
                hg, ag = self.simulate_match(home, away, MatchStage.GROUP)

                standing[home_name]["gf"] += hg
                standing[home_name]["ga"] += ag
                standing[home_name]["gd"] += hg - ag
                standing[away_name]["gf"] += ag
                standing[away_name]["ga"] += hg
                standing[away_name]["gd"] += ag - hg

                if hg > ag:
                    standing[home_name]["pts"] += 3
                elif hg == ag:
                    standing[home_name]["pts"] += 1
                    standing[away_name]["pts"] += 1
                else:
                    standing[away_name]["pts"] += 3

        return group_standings

    def _rank_group(self, standing: Dict) -> List[str]:
        """Rank teams: pts > gd > gf."""
        return sorted(
            standing.keys(),
            key=lambda t: (standing[t]["pts"], standing[t]["gd"], standing[t]["gf"]),
            reverse=True
        )

    # =========================================================================
    # Knockout Qualification
    # =========================================================================

    def _get_qualified_teams(self, group_standings: Dict) -> Tuple:
        """
        Determine qualified teams.
        Returns: (group_winners, all_top2, best_third)
        """
        group_winners = {}
        all_third = []

        for group, standing in group_standings.items():
            ranked = self._rank_group(standing)
            group_winners[group] = ranked[:2]
            if len(ranked) > 2:
                t = ranked[2]
                st = standing[t]
                all_third.append((group, t, st["pts"], st["gd"], st["gf"]))

        # Rank 3rd place teams: pts > gd > gf, take top 8
        all_third.sort(key=lambda t: (t[2], t[3], t[4]), reverse=True)
        best_third = all_third[:8]

        return group_winners, best_third

    # =========================================================================
    # Dynamic Bracket (2026 FIFA Official)
    # =========================================================================

    def _generate_r32(self, group_winners: Dict, best_third: List) -> List[Tuple]:
        """Generate R32 bracket. Returns [(home, away), ...]."""
        winners = {g: v[0] for g, v in group_winners.items()}
        runners = {g: v[1] for g, v in group_winners.items()}

        # Pool definitions for 3rd-place slots
        pools = ["ABcdf", "CDfgh", "ACefhI", "EhIjk",
                 "BDefiJ", "ADehIJ", "BCefGI", "CDeIJL"]

        # Assign best 3rd-place teams to pools in order
        third_assign = {}
        for i, (grp, name, pts, gd, gf) in enumerate(best_third):
            if i < len(pools):
                third_assign[pools[i]] = name

        def tp(pool):
            return third_assign.get(pool, "")

        r32 = [
            (runners.get("A",""), runners.get("B","")),  # 73
            (winners.get("E",""), tp("ABcdf")),           # 74
            (winners.get("F",""), runners.get("C","")),   # 75
            (winners.get("C",""), runners.get("F","")),   # 76
            (winners.get("I",""), tp("CDfgh")),           # 77
            (runners.get("E",""), runners.get("I","")),   # 78
            (winners.get("A",""), tp("ACefhI")),          # 79
            (winners.get("L",""), tp("EhIjk")),           # 80
            (winners.get("D",""), tp("BDefiJ")),          # 81
            (winners.get("G",""), tp("ADehIJ")),          # 82
            (runners.get("K",""), runners.get("L","")),   # 83
            (winners.get("H",""), runners.get("J","")),   # 84
            (winners.get("B",""), tp("BCefGI")),          # 85
            (winners.get("J",""), runners.get("H","")),   # 86
            (winners.get("K",""), tp("CDeIJL")),          # 87
            (runners.get("D",""), runners.get("G","")),   # 88
        ]
        return [(h, a) for h, a in r32 if h and a]

    def _generate_r16(self, r32_winners: List[str]) -> List[Tuple]:
        """R16: 8 matches from 16 R32 winners."""
        if len(r32_winners) < 16:
            return []
        w = r32_winners
        return [
            (w[1], w[4]), (w[0], w[2]), (w[3], w[5]), (w[6], w[7]),
            (w[10], w[11]), (w[8], w[9]), (w[13], w[15]), (w[12], w[14]),
        ]

    def _generate_qf(self, r16_winners: List[str]) -> List[Tuple]:
        if len(r16_winners) < 8:
            return []
        w = r16_winners
        return [(w[0], w[1]), (w[2], w[3]), (w[4], w[5]), (w[6], w[7])]

    def _generate_sf(self, qf_winners: List[str]) -> List[Tuple]:
        if len(qf_winners) < 4:
            return []
        return [(qf_winners[0], qf_winners[1]), (qf_winners[2], qf_winners[3])]

    def _generate_final(self, sf_winners: List[str]) -> List[Tuple]:
        if len(sf_winners) < 2:
            return []
        return [(sf_winners[0], sf_winners[1])]

    # =========================================================================
    # Tournament Simulation
    # =========================================================================

    def _simulate_knockout_round(
        self, matchups: List[Tuple], teams: Dict, stage: MatchStage
    ) -> List[str]:
        """Simulate a knockout round. Returns winners list."""
        winners = []
        for home_name, away_name in matchups:
            if not home_name or not away_name:
                winners.append("")
                continue
            home = teams.get(home_name)
            away = teams.get(away_name)
            if not home or not away:
                winners.append("")
                continue
            hg, ag = self.simulate_match(home, away, stage)
            if hg == ag:
                hg += 1  # Home team wins in extra time/penalties
            winners.append(home_name if hg > ag else away_name)
        return winners

    def simulate_tournament_run(
        self, teams: Dict[str, TeamStrength]
    ) -> Optional[str]:
        """Simulate one tournament. Returns champion name."""
        group_standings = self._simulate_group_stage(teams)
        group_winners, best_third = self._get_qualified_teams(group_standings)

        if len(best_third) < 8:
            return None

        r32 = self._generate_r32(group_winners, best_third)
        if len(r32) < 16:
            return None
        r32_w = self._simulate_knockout_round(r32, teams, MatchStage.R16)

        r16 = self._generate_r16(r32_w)
        if len(r16) < 8:
            return None
        r16_w = self._simulate_knockout_round(r16, teams, MatchStage.R16)

        qf = self._generate_qf(r16_w)
        if len(qf) < 4:
            return None
        qf_w = self._simulate_knockout_round(qf, teams, MatchStage.QUARTER)

        sf = self._generate_sf(qf_w)
        if len(sf) < 2:
            return None
        sf_w = self._simulate_knockout_round(sf, teams, MatchStage.SEMI)

        final = self._generate_final(sf_w)
        if not final:
            return None
        champ = self._simulate_knockout_round(final, teams, MatchStage.FINAL)
        return champ[0] if champ else None

    def simulate_tournament(self, n_runs: int = None) -> Dict[str, float]:
        """Monte Carlo simulation. Returns {team: champion_probability}."""
        runs = n_runs or self.n_simulations
        counts = defaultdict(int)

        for _ in range(runs):
            teams = {
                name: TeamStrength(
                    name=t.name, fifa_ranking=t.fifa_ranking,
                    attack=t.attack, defense=t.defense,
                    elo_rating=t.elo_rating, recent_form=t.recent_form,
                    injury_factor=t.injury_factor, morale=t.morale,
                    group=t.group, squad_value=t.squad_value,
                    host_factor=t.host_factor
                )
                for name, t in WORLD_CUP_TEAMS_2026.items()
            }
            champ = self.simulate_tournament_run(teams)
            if champ:
                counts[champ] += 1

        return dict(sorted(
            {t: c/runs for t, c in counts.items()}.items(),
            key=lambda x: x[1], reverse=True
        ))

    def get_detailed_odds(self, n_runs: int = None) -> Dict:
        """Return champion, semi-final, and quarter-final probabilities."""
        runs = n_runs or self.n_simulations
        champ_c = defaultdict(int)
        sf_c = defaultdict(int)
        qf_c = defaultdict(int)

        for _ in range(runs):
            teams = {
                name: TeamStrength(
                    name=t.name, fifa_ranking=t.fifa_ranking,
                    attack=t.attack, defense=t.defense,
                    elo_rating=t.elo_rating, recent_form=t.recent_form,
                    injury_factor=t.injury_factor, morale=t.morale,
                    group=t.group, squad_value=t.squad_value,
                    host_factor=t.host_factor
                )
                for name, t in WORLD_CUP_TEAMS_2026.items()
            }

            gs = self._simulate_group_stage(teams)
            gw, bt = self._get_qualified_teams(gs)
            if len(bt) < 8:
                continue

            r32 = self._generate_r32(gw, bt)
            r32_w = self._simulate_knockout_round(r32, teams, MatchStage.R16)
            for t in r32_w:
                qf_c[t] += 1

            r16 = self._generate_r16(r32_w)
            r16_w = self._simulate_knockout_round(r16, teams, MatchStage.R16)

            qf = self._generate_qf(r16_w)
            qf_w = self._simulate_knockout_round(qf, teams, MatchStage.QUARTER)
            for t in qf_w:
                sf_c[t] += 1

            sf = self._generate_sf(qf_w)
            sf_w = self._simulate_knockout_round(sf, teams, MatchStage.SEMI)
            final = self._generate_final(sf_w)
            champ = self._simulate_knockout_round(final, teams, MatchStage.FINAL)
            if champ:
                champ_c[champ[0]] += 1

        return {
            "champion": {t: c/runs for t, c in champ_c.items()},
            "semi_final": {t: c/runs for t, c in sf_c.items()},
            "quarter_final": {t: c/runs for t, c in qf_c.items()},
        }


if __name__ == "__main__":
    import time
    sim = WorldCupSimulator(n_simulations=100)
    print("Running 100-tournament Monte Carlo simulation...")
    t0 = time.time()
    odds = sim.simulate_tournament()
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s\n")
    print(f"{'Rank':<5} {'Team':<18} {'Chance':<8}")
    print("-" * 35)
    for i, (team, prob) in enumerate(list(odds.items())[:20], 1):
        bar = "#" * int(max(prob, 0) * 100)
        print(f"  #{i:<2} {team:<18} {prob:<7.2%} {bar}")
