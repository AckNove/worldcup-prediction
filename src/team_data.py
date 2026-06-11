"""
2026 World Cup Team Data (Improved)
===============================
Data sources:
  - FIFA Rankings (May 2026)
  - Transfermarkt squad values (April 2026)
  - Official draw & schedule
  - Attack/defense: weighted formula using squad value + FIFA rank + Elo
"""
from typing import Dict, List, Tuple
from .poisson_model import TeamStrength

WORLD_CUP_TEAMS_2026: Dict[str, TeamStrength] = {

    # ===== Group A =====
    "Mexico": TeamStrength(
        name="Mexico", fifa_ranking=15, group="A",
        elo_rating=1681, recent_form=1.0,
        morale=1.12, attack=1.21, defense=0.936,
        squad_value=165.8, host_factor=1.15,
    ),
    "South Korea": TeamStrength(
        name="South Korea", fifa_ranking=25, group="A",
        elo_rating=1589, recent_form=1.02,
        morale=1.0, attack=1.132, defense=1.002,
        squad_value=136.75, host_factor=1.0,
    ),
    "South Africa": TeamStrength(
        name="South Africa", fifa_ranking=55, group="A",
        elo_rating=1420, recent_form=0.95,
        morale=1.05, attack=0.871, defense=1.222,
        squad_value=41.15, host_factor=1.0,
    ),
    "Czechia": TeamStrength(
        name="Czechia", fifa_ranking=41, group="A",
        elo_rating=1501, recent_form=0.96,
        morale=0.98, attack=1.088, defense=1.039,
        squad_value=180.8, host_factor=1.0,
    ),

    # ===== Group B =====
    "Canada": TeamStrength(
        name="Canada", fifa_ranking=30, group="B",
        elo_rating=1556, recent_form=1.02,
        morale=1.1, attack=1.102, defense=1.027,
        squad_value=129.88, host_factor=1.15,
    ),
    "Switzerland": TeamStrength(
        name="Switzerland", fifa_ranking=19, group="B",
        elo_rating=1649, recent_form=0.98,
        morale=0.97, attack=1.257, defense=0.897,
        squad_value=322.1, host_factor=1.0,
    ),
    "Qatar": TeamStrength(
        name="Qatar", fifa_ranking=49, group="B",
        elo_rating=1440, recent_form=0.95,
        morale=0.95, attack=0.81, defense=1.273,
        squad_value=18.3, host_factor=1.0,
    ),
    "Bosnia and Herzegovina": TeamStrength(
        name="Bosnia and Herzegovina", fifa_ranking=58, group="B",
        elo_rating=1400, recent_form=0.93,
        morale=1.02, attack=0.972, defense=1.137,
        squad_value=127.1, host_factor=1.0,
    ),

    # ===== Group C =====
    "Brazil": TeamStrength(
        name="Brazil", fifa_ranking=6, group="C",
        elo_rating=1761, recent_form=1.08,
        morale=1.05, attack=1.421, defense=0.759,
        squad_value=778.5, host_factor=1.0,
    ),
    "Morocco": TeamStrength(
        name="Morocco", fifa_ranking=8, group="C",
        elo_rating=1756, recent_form=1.04,
        morale=1.08, attack=1.359, defense=0.811,
        squad_value=456.0, host_factor=1.0,
    ),
    "Scotland": TeamStrength(
        name="Scotland", fifa_ranking=43, group="C",
        elo_rating=1498, recent_form=0.95,
        morale=1.0, attack=1.091, defense=1.036,
        squad_value=198.15, host_factor=1.0,
    ),
    "Haiti": TeamStrength(
        name="Haiti", fifa_ranking=82, group="C",
        elo_rating=1260, recent_form=0.9,
        morale=1.08, attack=0.774, defense=1.303,
        squad_value=55.1, host_factor=1.0,
    ),

    # ===== Group D =====
    "USA": TeamStrength(
        name="USA", fifa_ranking=16, group="D",
        elo_rating=1673, recent_form=1.04,
        morale=1.15, attack=1.284, defense=0.874,
        squad_value=356.7, host_factor=1.15,
    ),
    "Australia": TeamStrength(
        name="Australia", fifa_ranking=27, group="D",
        elo_rating=1581, recent_form=0.97,
        morale=1.0, attack=1.022, defense=1.095,
        squad_value=50.48, host_factor=1.0,
    ),
    "Paraguay": TeamStrength(
        name="Paraguay", fifa_ranking=40, group="D",
        elo_rating=1504, recent_form=0.96,
        morale=0.98, attack=1.062, defense=1.061,
        squad_value=135.2, host_factor=1.0,
    ),
    "Turkiye": TeamStrength(
        name="Turkiye", fifa_ranking=22, group="D",
        elo_rating=1599, recent_form=1.02,
        morale=1.02, attack=1.264, defense=0.891,
        squad_value=440.2, host_factor=1.0,
    ),

    # ===== Group E =====
    "Germany": TeamStrength(
        name="Germany", fifa_ranking=10, group="E",
        elo_rating=1730, recent_form=1.04,
        morale=1.02, attack=1.399, defense=0.777,
        squad_value=773.5, host_factor=1.0,
    ),
    "Ecuador": TeamStrength(
        name="Ecuador", fifa_ranking=23, group="E",
        elo_rating=1595, recent_form=1.0,
        morale=0.99, attack=1.241, defense=0.91,
        squad_value=366.73, host_factor=1.0,
    ),
    "Ivory Coast": TeamStrength(
        name="Ivory Coast", fifa_ranking=34, group="E",
        elo_rating=1533, recent_form=0.98,
        morale=1.0, attack=1.206, defense=0.94,
        squad_value=425.9, host_factor=1.0,
    ),
    "Curacao": TeamStrength(
        name="Curacao", fifa_ranking=89, group="E",
        elo_rating=1220, recent_form=0.85,
        morale=1.15, attack=0.674, defense=1.388,
        squad_value=28.38, host_factor=1.0,
    ),

    # ===== Group F =====
    "Netherlands": TeamStrength(
        name="Netherlands", fifa_ranking=7, group="F",
        elo_rating=1758, recent_form=1.05,
        morale=1.02, attack=1.416, defense=0.763,
        squad_value=766.0, host_factor=1.0,
    ),
    "Japan": TeamStrength(
        name="Japan", fifa_ranking=18, group="F",
        elo_rating=1660, recent_form=1.04,
        morale=1.05, attack=1.243, defense=0.909,
        squad_value=264.2, host_factor=1.0,
    ),
    "Tunisia": TeamStrength(
        name="Tunisia", fifa_ranking=44, group="F",
        elo_rating=1483, recent_form=0.95,
        morale=1.0, attack=0.946, defense=1.159,
        squad_value=52.0, host_factor=1.0,
    ),
    "Sweden": TeamStrength(
        name="Sweden", fifa_ranking=38, group="F",
        elo_rating=1515, recent_form=1.01,
        morale=1.0, attack=1.173, defense=0.968,
        squad_value=363.98, host_factor=1.0,
    ),

    # ===== Group G =====
    "Belgium": TeamStrength(
        name="Belgium", fifa_ranking=9, group="G",
        elo_rating=1735, recent_form=0.98,
        morale=0.95, attack=1.365, defense=0.806,
        squad_value=534.2, host_factor=1.0,
    ),
    "Iran": TeamStrength(
        name="Iran", fifa_ranking=21, group="G",
        elo_rating=1615, recent_form=1.0,
        morale=1.02, attack=1.017, defense=1.099,
        squad_value=36.78, host_factor=1.0,
    ),
    "Egypt": TeamStrength(
        name="Egypt", fifa_ranking=29, group="G",
        elo_rating=1563, recent_form=0.98,
        morale=1.02, attack=1.088, defense=1.039,
        squad_value=108.0, host_factor=1.0,
    ),
    "New Zealand": TeamStrength(
        name="New Zealand", fifa_ranking=92, group="G",
        elo_rating=1200, recent_form=0.88,
        morale=1.0, attack=0.634, defense=1.422,
        squad_value=22.2, host_factor=1.0,
    ),

    # ===== Group H =====
    "Spain": TeamStrength(
        name="Spain", fifa_ranking=2, group="H",
        elo_rating=1876, recent_form=1.1,
        morale=1.05, attack=1.525, defense=0.671,
        squad_value=1310.0, host_factor=1.0,
    ),
    "Uruguay": TeamStrength(
        name="Uruguay", fifa_ranking=17, group="H",
        elo_rating=1673, recent_form=1.0,
        morale=1.02, attack=1.284, defense=0.874,
        squad_value=366.45, host_factor=1.0,
    ),
    "Saudi Arabia": TeamStrength(
        name="Saudi Arabia", fifa_ranking=52, group="H",
        elo_rating=1435, recent_form=0.96,
        morale=1.02, attack=0.843, defense=1.245,
        squad_value=27.63, host_factor=1.0,
    ),
    "Cape Verde": TeamStrength(
        name="Cape Verde", fifa_ranking=70, group="H",
        elo_rating=1330, recent_form=0.92,
        morale=1.05, attack=0.81, defense=1.273,
        squad_value=45.15, host_factor=1.0,
    ),

    # ===== Group I =====
    "France": TeamStrength(
        name="France", fifa_ranking=1, group="I",
        elo_rating=1877, recent_form=1.12,
        morale=1.1, attack=1.532, defense=0.665,
        squad_value=1360.0, host_factor=1.0,
    ),
    "Senegal": TeamStrength(
        name="Senegal", fifa_ranking=14, group="I",
        elo_rating=1689, recent_form=1.0,
        morale=1.02, attack=1.324, defense=0.841,
        squad_value=474.0, host_factor=1.0,
    ),
    "Norway": TeamStrength(
        name="Norway", fifa_ranking=31, group="I",
        elo_rating=1551, recent_form=1.02,
        morale=1.0, attack=1.237, defense=0.913,
        squad_value=504.0, host_factor=1.0,
    ),
    "Iraq": TeamStrength(
        name="Iraq", fifa_ranking=68, group="I",
        elo_rating=1350, recent_form=0.93,
        morale=1.05, attack=0.734, defense=1.337,
        squad_value=19.18, host_factor=1.0,
    ),

    # ===== Group J =====
    "Argentina": TeamStrength(
        name="Argentina", fifa_ranking=3, group="J",
        elo_rating=1875, recent_form=1.1,
        morale=1.12, attack=1.466, defense=0.72,
        squad_value=761.2, host_factor=1.0,
    ),
    "Austria": TeamStrength(
        name="Austria", fifa_ranking=24, group="J",
        elo_rating=1593, recent_form=1.02,
        morale=1.0, attack=1.204, defense=0.942,
        squad_value=263.4, host_factor=1.0,
    ),
    "Algeria": TeamStrength(
        name="Algeria", fifa_ranking=28, group="J",
        elo_rating=1564, recent_form=0.98,
        morale=1.02, attack=1.168, defense=0.972,
        squad_value=227.75, host_factor=1.0,
    ),
    "Jordan": TeamStrength(
        name="Jordan", fifa_ranking=67, group="J",
        elo_rating=1360, recent_form=0.92,
        morale=1.05, attack=0.721, defense=1.348,
        squad_value=15.98, host_factor=1.0,
    ),

    # ===== Group K =====
    "Portugal": TeamStrength(
        name="Portugal", fifa_ranking=5, group="K",
        elo_rating=1764, recent_form=1.06,
        morale=1.04, attack=1.435, defense=0.747,
        squad_value=864.5, host_factor=1.0,
    ),
    "Colombia": TeamStrength(
        name="Colombia", fifa_ranking=13, group="K",
        elo_rating=1693, recent_form=1.04,
        morale=1.03, attack=1.281, defense=0.877,
        squad_value=300.5, host_factor=1.0,
    ),
    "Uzbekistan": TeamStrength(
        name="Uzbekistan", fifa_ranking=50, group="K",
        elo_rating=1465, recent_form=0.95,
        morale=1.05, attack=0.945, defense=1.16,
        squad_value=63.75, host_factor=1.0,
    ),
    "DR Congo": TeamStrength(
        name="DR Congo", fifa_ranking=46, group="K",
        elo_rating=1478, recent_form=0.93,
        morale=1.0, attack=1.05, defense=1.071,
        squad_value=153.4, host_factor=1.0,
    ),

    # ===== Group L =====
    "England": TeamStrength(
        name="England", fifa_ranking=4, group="L",
        elo_rating=1826, recent_form=1.08,
        morale=1.05, attack=1.524, defense=0.672,
        squad_value=1620.0, host_factor=1.0,
    ),
    "Croatia": TeamStrength(
        name="Croatia", fifa_ranking=11, group="L",
        elo_rating=1717, recent_form=0.98,
        morale=1.02, attack=1.288, defense=0.871,
        squad_value=282.3, host_factor=1.0,
    ),
    "Ghana": TeamStrength(
        name="Ghana", fifa_ranking=56, group="L",
        elo_rating=1425, recent_form=0.95,
        morale=1.0, attack=1.032, defense=1.086,
        squad_value=199.28, host_factor=1.0,
    ),
    "Panama": TeamStrength(
        name="Panama", fifa_ranking=33, group="L",
        elo_rating=1541, recent_form=0.96,
        morale=1.02, attack=0.946, defense=1.158,
        squad_value=32.4, host_factor=1.0,
    ),
}


GROUP_MEMBERS: Dict[str, List[str]] = {
    "A": ['Mexico', 'South Korea', 'South Africa', 'Czechia'],
    "B": ['Canada', 'Switzerland', 'Qatar', 'Bosnia and Herzegovina'],
    "C": ['Brazil', 'Morocco', 'Scotland', 'Haiti'],
    "D": ['USA', 'Australia', 'Paraguay', 'Turkiye'],
    "E": ['Germany', 'Ecuador', 'Ivory Coast', 'Curacao'],
    "F": ['Netherlands', 'Japan', 'Tunisia', 'Sweden'],
    "G": ['Belgium', 'Iran', 'Egypt', 'New Zealand'],
    "H": ['Spain', 'Uruguay', 'Saudi Arabia', 'Cape Verde'],
    "I": ['France', 'Senegal', 'Norway', 'Iraq'],
    "J": ['Argentina', 'Austria', 'Algeria', 'Jordan'],
    "K": ['Portugal', 'Colombia', 'Uzbekistan', 'DR Congo'],
    "L": ['England', 'Croatia', 'Ghana', 'Panama'],
}


GROUP_STAGE_MATCHUPS: List[Tuple[str, str, int]] = [
    ("Mexico", "South Africa", 1),
    ("South Korea", "Czechia", 1),
    ("Czechia", "South Africa", 2),
    ("Mexico", "South Korea", 2),
    ("Czechia", "Mexico", 3),
    ("South Africa", "South Korea", 3),
    ("Canada", "Bosnia and Herzegovina", 1),
    ("Qatar", "Switzerland", 1),
    ("Bosnia and Herzegovina", "Switzerland", 2),
    ("Canada", "Qatar", 2),
    ("Switzerland", "Canada", 3),
    ("Bosnia and Herzegovina", "Qatar", 3),
    ("Brazil", "Morocco", 1),
    ("Haiti", "Scotland", 1),
    ("Scotland", "Morocco", 2),
    ("Brazil", "Haiti", 2),
    ("Scotland", "Brazil", 3),
    ("Morocco", "Haiti", 3),
    ("USA", "Paraguay", 1),
    ("Australia", "Turkiye", 1),
    ("USA", "Australia", 2),
    ("Turkiye", "Paraguay", 2),
    ("Turkiye", "USA", 3),
    ("Paraguay", "Australia", 3),
    ("Germany", "Curacao", 1),
    ("Ivory Coast", "Ecuador", 1),
    ("Germany", "Ivory Coast", 2),
    ("Ecuador", "Curacao", 2),
    ("Ecuador", "Germany", 3),
    ("Curacao", "Ivory Coast", 3),
    ("Netherlands", "Japan", 1),
    ("Sweden", "Tunisia", 1),
    ("Netherlands", "Sweden", 2),
    ("Tunisia", "Japan", 2),
    ("Tunisia", "Netherlands", 3),
    ("Japan", "Sweden", 3),
    ("Belgium", "Egypt", 1),
    ("Iran", "New Zealand", 1),
    ("Belgium", "Iran", 2),
    ("New Zealand", "Egypt", 2),
    ("New Zealand", "Belgium", 3),
    ("Egypt", "Iran", 3),
    ("Spain", "Cape Verde", 1),
    ("Saudi Arabia", "Uruguay", 1),
    ("Spain", "Saudi Arabia", 2),
    ("Uruguay", "Cape Verde", 2),
    ("Uruguay", "Spain", 3),
    ("Cape Verde", "Saudi Arabia", 3),
    ("France", "Senegal", 1),
    ("Iraq", "Norway", 1),
    ("France", "Iraq", 2),
    ("Norway", "Senegal", 2),
    ("Norway", "France", 3),
    ("Senegal", "Iraq", 3),
    ("Argentina", "Algeria", 1),
    ("Austria", "Jordan", 1),
    ("Argentina", "Austria", 2),
    ("Jordan", "Algeria", 2),
    ("Jordan", "Argentina", 3),
    ("Algeria", "Austria", 3),
    ("Portugal", "DR Congo", 1),
    ("Uzbekistan", "Colombia", 1),
    ("Portugal", "Uzbekistan", 2),
    ("Colombia", "DR Congo", 2),
    ("Colombia", "Portugal", 3),
    ("DR Congo", "Uzbekistan", 3),
    ("England", "Croatia", 1),
    ("Ghana", "Panama", 1),
    ("England", "Ghana", 2),
    ("Panama", "Croatia", 2),
    ("Panama", "England", 3),
    ("Croatia", "Ghana", 3),
]


# Old-style knockout predictions (for demo/web compat)
KNOCKOUT_MATCHUPS: List[Tuple[str, str, str]] = [
    ("France", "Uruguay", "R32"), ("Spain", "Australia", "R32"),
    ("Argentina", "South Korea", "R32"), ("England", "Sweden", "R32"),
    ("Brazil", "Czechia", "R32"), ("Portugal", "Japan", "R32"),
    ("Germany", "Paraguay", "R32"), ("Netherlands", "Turkiye", "R32"),
    ("France", "Spain", "R16"), ("Argentina", "England", "R16"),
    ("Brazil", "Portugal", "R16"), ("Germany", "Netherlands", "R16"),
    ("France", "Argentina", "QF"), ("Brazil", "Germany", "QF"),
    ("France", "Brazil", "SF"),
    ("Argentina", "France", "FIN"),
]

# Utility functions
def get_team(name: str) -> TeamStrength:
    """Get team by name."""
    if name in WORLD_CUP_TEAMS_2026:
        return WORLD_CUP_TEAMS_2026[name]
    return TeamStrength(name=name, attack=1.0, defense=1.0,
                        recent_form=1.0, morale=1.0, injury_factor=1.0,
                        squad_value=50.0, host_factor=1.0)


def get_teams_by_group(group: str) -> List[TeamStrength]:
    """Get all teams in a group."""
    return [t for t in WORLD_CUP_TEAMS_2026.values()
            if t.group == group.upper()]


def list_all_teams() -> List[str]:
    """List all team names."""
    return list(WORLD_CUP_TEAMS_2026.keys())