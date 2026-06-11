"""
Poisson-based Football Score Prediction Model
==============================================

核心原理：
  足球比赛的进球数服从 Poisson 分布。
  对于一场比赛，主队和客队的预期进球数分别为 λ_home 和 λ_away。

  λ_home = 主场优势 × 主队攻击力 × 客队防守力 × 联赛平均主队进球
  λ_away = 客队攻击力 × 主队防守力 × 联赛平均客队进球

  比分 (i,j) 的概率 = Poisson(i, λ_home) × Poisson(j, λ_away)

增强功能：
  - 球队 Elo 动态评分系统
  - 近期状态加权
  - 伤病影响系数
  - 比赛重要性系数（小组赛/淘汰赛）
  - 蒙特卡洛仿真
"""

import math
import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict


class MatchStage(Enum):
    """比赛阶段"""
    GROUP = "group"          # 小组赛
    R16 = "round_of_16"      # 16强
    QUARTER = "quarter"      # 1/4决赛
    SEMI = "semi"            # 半决赛
    FINAL = "final"          # 决赛


@dataclass
class TeamStrength:
    """球队实力参数"""
    name: str
    fifa_ranking: int = 100
    attack: float = 1.0      # 攻击力 (相对联赛平均)
    defense: float = 1.0     # 防守力 (相对联赛平均, 越小越好)
    elo_rating: float = 1500.0  # Elo 评分
    recent_form: float = 1.0    # 近期状态 (0.8-1.2)
    injury_factor: float = 1.0  # 伤病影响 (0.7-1.0)
    morale: float = 1.0         # 士气/氛围 (0.8-1.2)
    group: str = ""             # 世界杯小组
    squad_value: float = 50.0   # 球队总身价 (百万欧元), Transfermarkt数据
    host_factor: float = 1.0    # 东道主加成 (1.0=普通, 1.15=东道主)

    def effective_attack(self, stage: MatchStage = MatchStage.GROUP) -> float:
        """有效攻击力（综合各项因素）"""
        importance_factor = self._stage_factor(stage)
        return self.attack * self.recent_form * self.morale * importance_factor * self.host_factor

    def effective_defense(self, stage: MatchStage = MatchStage.GROUP) -> float:
        """有效防守力"""
        importance_factor = self._stage_factor(stage)
        return self.defense * self.recent_form * self.injury_factor / (importance_factor ** 0.5) / (self.host_factor ** 0.3)

    @staticmethod
    def _stage_factor(stage: MatchStage) -> float:
        """比赛阶段系数：淘汰赛阶段球队会更谨慎/更拼搏"""
        factors = {
            MatchStage.GROUP: 1.0,
            MatchStage.R16: 1.05,
            MatchStage.QUARTER: 1.08,
            MatchStage.SEMI: 1.12,
            MatchStage.FINAL: 1.15,
        }
        return factors[stage]


@dataclass
class MatchResult:
    """单场比赛结果"""
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    stage: MatchStage = MatchStage.GROUP

    @property
    def winner(self) -> Optional[str]:
        if self.home_goals > self.away_goals:
            return self.home_team
        elif self.away_goals > self.home_goals:
            return self.away_team
        return None

    @property
    def is_draw(self) -> bool:
        return self.home_goals == self.away_goals


@dataclass
class PredictionResult:
    """预测结果（含增强输出）"""
    home_team: str
    away_team: str
    lambda_home: float          # 预期主队进球
    lambda_away: float          # 预期客队进球
    home_win_prob: float        # 主胜概率
    draw_prob: float            # 平局概率
    away_win_prob: float        # 客胜概率
    most_likely_score: Tuple[int, int]  # 最可能比分
    score_probabilities: Dict[Tuple[int, int], float] = field(default_factory=dict)
    confidence: float = 0.0     # 预测置信度 (0-1)
    max_goals: int = 8          # 最大进球数上限
    simulation_results: Dict = field(default_factory=dict)

    # ── 总进球数分布 ──────────────────────────────────
    @property
    def total_goals_distribution(self) -> Dict[int, float]:
        """总进球数概率分布: {0: 4.8%, 1: 13.2%, ...}"""
        dist = {}
        total = self.max_goals * 2  # 最大可能总进球
        for n in range(total + 1):
            prob = 0.0
            for i in range(0, self.max_goals + 1):
                j = n - i
                if 0 <= j <= self.max_goals:
                    prob += self.score_probabilities.get((i, j), 0.0)
            if prob > 0.0001:
                dist[n] = prob
        # 7+球合并
        seven_plus = sum(v for k, v in dist.items() if k >= 7)
        dist = {k: v for k, v in dist.items() if k < 7}
        if seven_plus > 0.0001:
            dist[7] = round(seven_plus, 4)
        return dict(sorted(dist.items()))

    @property
    def total_goals_chinese(self) -> Dict[str, float]:
        """总进球数中文格式: {'0球': 4.8%, '1球': 13.2%, ...}"""
        dist = self.total_goals_distribution
        result = OrderedDict()
        for k, v in dist.items():
            if k == 7:
                result["7+球"] = round(v * 100, 1)
            else:
                result[f"{k}球"] = round(v * 100, 1)
        return result

    # ── 大小球 (Over/Under) ──────────────────────────
    @property
    def over_under(self) -> Dict[str, float]:
        """大小球概率"""
        dist = self.total_goals_distribution
        p_le_2 = sum(v for k, v in dist.items() if k <= 2)
        p_le_3 = sum(v for k, v in dist.items() if k <= 3)
        return {
            "大2.5球": round((1 - p_le_2) * 100, 1),
            "小2.5球": round(p_le_2 * 100, 1),
            "大3.5球": round((1 - p_le_3) * 100, 1),
            "小3.5球": round(p_le_3 * 100, 1),
        }

    # ── 双方进球 (Both Teams To Score) ────────────────
    @property
    def btts(self) -> Dict[str, float]:
        """双方进球概率"""
        p_home_0 = sum(self.score_probabilities.get((0, j), 0.0) for j in range(self.max_goals + 1))
        p_away_0 = sum(self.score_probabilities.get((i, 0), 0.0) for i in range(self.max_goals + 1))

        p_both = (1 - p_home_0) * (1 - p_away_0)
        p_either = 1 - (p_home_0 * p_away_0)
        p_one_only = p_either - p_both

        return {
            "both_teams_to_score": round(p_both * 100, 1),
            "either_team_to_score": round(p_either * 100, 1),
            "one_team_to_score": round(p_one_only * 100, 1),
        }

    # ── 竞彩比分格式 (含胜其他/平其他/负其他) ──────────
    CJK_HOME_SCORES = [
        (1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (3, 2),
        (4, 0), (4, 1), (4, 2), (5, 0), (5, 1), (5, 2),
    ]
    CJK_DRAW_SCORES = [(0, 0), (1, 1), (2, 2), (3, 3)]
    CJK_AWAY_SCORES = [
        (0, 1), (0, 2), (1, 2), (0, 3), (1, 3), (2, 3),
        (0, 4), (1, 4), (2, 4), (0, 5), (1, 5), (2, 5),
    ]

    @property
    def cjklottery_format(self) -> Dict[str, Any]:
        """竞彩比分格式 (映射胜其他/平其他/负其他)"""
        # 主胜比分
        home_scores = OrderedDict()
        home_known_sum = 0.0
        for h, a in self.CJK_HOME_SCORES:
            p = self.score_probabilities.get((h, a), 0.0)
            home_scores[f"{h}-{a}"] = round(p * 100, 1)
            home_known_sum += p

        # 平局比分
        draw_scores = OrderedDict()
        draw_known_sum = 0.0
        for h, a in self.CJK_DRAW_SCORES:
            p = self.score_probabilities.get((h, a), 0.0)
            draw_scores[f"{h}-{a}"] = round(p * 100, 1)
            draw_known_sum += p

        # 客胜比分
        away_scores = OrderedDict()
        away_known_sum = 0.0
        for h, a in self.CJK_AWAY_SCORES:
            p = self.score_probabilities.get((h, a), 0.0)
            away_scores[f"{h}-{a}"] = round(p * 100, 1)
            away_known_sum += p

        # 胜其他 = 所有主胜概率 - 已知主胜比分概率之和
        home_other = max(0, self.home_win_prob - home_known_sum)
        draw_other = max(0, self.draw_prob - draw_known_sum)
        away_other = max(0, self.away_win_prob - away_known_sum)

        home_scores["胜其他"] = round(home_other * 100, 1)
        draw_scores["平其他"] = round(draw_other * 100, 1)
        away_scores["负其他"] = round(away_other * 100, 1)

        return {
            "home_win_scores": home_scores,
            "draw_scores": draw_scores,
            "away_win_scores": away_scores,
        }

    # ── 帮助方法 ──────────────────────────────────────
    def score_prob(self, home_goals: int, away_goals: int) -> float:
        """获取指定比分的概率"""
        return self.score_probabilities.get((home_goals, away_goals), 0.0)

    def top_scores(self, n: int = 5) -> List[Tuple[Tuple[int, int], float]]:
        """返回概率最高的 n 个比分"""
        sorted_scores = sorted(
            self.score_probabilities.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_scores[:n]

    def top_scores_formatted(self, n: int = 10) -> List[Dict]:
        """返回格式化TOP比分列表 [{'score': '2-1', 'prob': 8.7}, ...]"""
        return [
            {"score": f"{h}-{a}", "prob": f"{p*100:.1f}%"}
            for (h, a), p in self.top_scores(n)
        ]

    def win_draw_win_formatted(self) -> Dict[str, str]:
        """胜平负概率带%格式"""
        return {
            "主胜概率": f"{self.home_win_prob*100:.1f}%",
            "平局概率": f"{self.draw_prob*100:.1f}%",
            "客胜概率": f"{self.away_win_prob*100:.1f}%",
        }

    def confidence_label(self) -> str:
        """置信度中文标签（校准版 v2，最高85%）"""
        score = self.confidence * 100
        if score >= 72:
            return "非常高"
        elif score >= 58:
            return "中高等"
        elif score >= 44:
            return "中等"
        elif score >= 30:
            return "中低等"
        else:
            return "较低"

    def summary(self) -> str:
        """生成预测摘要"""
        lines = [
            f"{'='*60}",
            f"  {self.home_team} vs {self.away_team}",
            f"{'='*60}",
            f"  预期进球:  {self.home_team} {self.lambda_home:.2f} — {self.lambda_away:.2f} {self.away_team}",
            f"  胜平负概率: 主胜 {self.home_win_prob:.1%} | 平局 {self.draw_prob:.1%} | 客胜 {self.away_win_prob:.1%}",
            f"  最可能比分: {self.home_team} {self.most_likely_score[0]}-{self.most_likely_score[1]} {self.away_team}",
            f"  置信度: {self.confidence:.1%} ({self.confidence_label()})",
        ]

        lines.append(f"\n  前5最可能比分:")
        for (h, a), prob in self.top_scores(5):
            lines.append(f"    {self.home_team} {h}-{a} {self.away_team}  → {prob:.1%}")

        lines.append(f"\n  总进球数概率:")
        for k, v in self.total_goals_chinese.items():
            lines.append(f"    {k}: {v}%")

        lines.append(f"\n  大小球:")
        ou = self.over_under
        lines.append(f"    大2.5球: {ou['大2.5球']}% | 小2.5球: {ou['小2.5球']}%")
        lines.append(f"    大3.5球: {ou['大3.5球']}% | 小3.5球: {ou['小3.5球']}%")

        btts = self.btts
        lines.append(f"\n  双方进球:")
        lines.append(f"    双方都进球: {btts['both_teams_to_score']}%")
        lines.append(f"    仅一队进球: {btts['one_team_to_score']}%")

        lines.append(f"{'='*60}")
        return "\n".join(lines)


class PoissonPredictor:
    """
    Poisson 分布比分预测器
    """

    def __init__(self, home_advantage: float = 1.1):
        """
        参数:
            home_advantage: 主场优势系数 (默认1.1，即主场多进10%)
        """
        self.home_advantage = home_advantage
        self.league_avg_home_goals = 1.35   # 联赛平均主队进球
        self.league_avg_away_goals = 1.05   # 联赛平均客队进球

    @staticmethod
    def poisson_prob(k: int, lam: float) -> float:
        """计算 Poisson 概率 P(X=k) = λ^k * e^(-λ) / k!"""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        # 使用 log 计算防止溢出
        log_prob = k * math.log(lam) - lam - math.log(math.factorial(k))
        return math.exp(log_prob)

    def expected_goals(
        self,
        home: TeamStrength,
        away: TeamStrength,
        stage: MatchStage = MatchStage.GROUP
    ) -> Tuple[float, float]:
        """
        计算预期进球数

        λ_home = 主场优势 × (主队攻击/平均攻击) × (客队防守/平均防守) × 平均主队进球
        λ_away = (客队攻击/平均攻击) × (主队防守/平均防守) × 平均客队进球
        """
        lambda_home = (
            self.home_advantage *
            (home.effective_attack(stage) / 1.0) *
            (away.effective_defense(stage) / 1.0) *
            self.league_avg_home_goals
        )

        lambda_away = (
            (away.effective_attack(stage) / 1.0) *
            (home.effective_defense(stage) / 1.0) *
            self.league_avg_away_goals
        )

        return lambda_home, lambda_away

    def predict(
        self,
        home: TeamStrength,
        away: TeamStrength,
        stage: MatchStage = MatchStage.GROUP,
        max_goals: int = 8
    ) -> PredictionResult:
        """
        预测一场比赛的结果

        参数:
            home: 主队实力
            away: 客队实力
            stage: 比赛阶段
            max_goals: 计算比分时考虑的最大进球数

        返回:
            PredictionResult 包含完整的预测信息
        """
        lambda_home, lambda_away = self.expected_goals(home, away, stage)

        # 计算所有可能比分的概率
        score_probs = {}
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0

        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                prob = self.poisson_prob(i, lambda_home) * self.poisson_prob(j, lambda_away)
                score_probs[(i, j)] = prob

                if i > j:
                    home_win_prob += prob
                elif i == j:
                    draw_prob += prob
                else:
                    away_win_prob += prob

        # 最可能比分
        most_likely = max(score_probs, key=score_probs.get)

        # ── 置信度计算（多维度，校准版 v3） ──
        # 回测发现原版在中等置信度(50-70%)偏高约25%，v2版本矫枉过正压得太低。
        # v3目标：确定性强的场次 55-75%，普通场次 35-55%，不确定场次 15-35%
        best_prob = score_probs[most_likely]

        # 维度1：最可能比分的集中度
        # 前5比分概率之和 vs 最高比分，衡量分布集中程度
        top5 = sorted(score_probs.values(), reverse=True)[:5]
        top1 = top5[0]
        top5_sum = sum(top5)
        concentration = top1 / top5_sum if top5_sum > 0 else 0.2
        # 归一化：集中度15%-50%对应0-1，世界杯一般在20-35%
        dimension1 = min(max((concentration - 0.15) / 0.35, 0.0), 1.0)

        # 维度2：胜平负结果的确定性（校准基准）
        wdw_max = max(home_win_prob, draw_prob, away_win_prob)
        # 基准40%（世界杯胜负差不多各1/3），超过70%才算高置信度
        dimension2 = min(max((wdw_max - 0.40) / 0.35, 0.0), 1.0)

        # 平局惩罚：平局概率>30%时降低置信度（平局最难预测）
        draw_penalty = max(0, draw_prob - 0.30) * 1.2
        dimension2 = max(0, dimension2 - draw_penalty)

        # 维度3：预期进球差距（实力差距）
        goal_diff = abs(lambda_home - lambda_away)
        # 进球差0.2~1.5对应0~1，超过1.5的按1计
        dimension3 = min(max((goal_diff - 0.2) / 1.3, 0.0), 1.0)

        # 维度4：总进球数合理性（偏极端则适当降低）
        total_expected = lambda_home + lambda_away
        # 世界杯场均约2.5球，偏离1.5球以上降低置信度
        total_deviation = abs(total_expected - 2.5)
        dimension4 = max(0.5, 1.0 - total_deviation * 0.2)

        # 综合置信度
        confidence = (
            0.30 * dimension1 +
            0.45 * dimension2 +
            0.15 * dimension3 +
            0.10 * dimension4
        )
        # 整体基础抬升 + 适度缩放（让输出分布更合理）
        confidence = 0.15 + confidence * 0.70

        # 严格范围限制：最高82%（不存在完全确定的比赛）
        confidence = max(0.12, min(confidence, 0.82))

        return PredictionResult(
            home_team=home.name,
            away_team=away.name,
            lambda_home=lambda_home,
            lambda_away=lambda_away,
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            most_likely_score=most_likely,
            score_probabilities=score_probs,
            confidence=confidence,
            max_goals=max_goals,
        )

    def monte_carlo_simulation(
        self,
        home: TeamStrength,
        away: TeamStrength,
        stage: MatchStage = MatchStage.GROUP,
        n_simulations: int = 10000
    ) -> Dict:
        """
        蒙特卡洛仿真：多次模拟比赛，统计各种结果分布

        比纯Poisson计算更能捕捉极端情况和相关性
        """
        lambda_home, lambda_away = self.expected_goals(home, away, stage)

        results = {
            "home_wins": 0,
            "draws": 0,
            "away_wins": 0,
            "total_goals": [],
            "scorelines": {},
            "home_goals_dist": {},
            "away_goals_dist": {},
        }

        for _ in range(n_simulations):
            h_goals = random.poissonvariate(lambda_home)
            a_goals = random.poissonvariate(lambda_away)

            results["total_goals"].append(h_goals + a_goals)

            scoreline = f"{h_goals}-{a_goals}"
            results["scorelines"][scoreline] = results["scorelines"].get(scoreline, 0) + 1

            results["home_goals_dist"][h_goals] = results["home_goals_dist"].get(h_goals, 0) + 1
            results["away_goals_dist"][a_goals] = results["away_goals_dist"].get(a_goals, 0) + 1

            if h_goals > a_goals:
                results["home_wins"] += 1
            elif h_goals == a_goals:
                results["draws"] += 1
            else:
                results["away_wins"] += 1

        # 归一化
        for key in ["home_wins", "draws", "away_wins"]:
            results[key] /= n_simulations
        for d in [results["scorelines"], results["home_goals_dist"], results["away_goals_dist"]]:
            for k in d:
                d[k] /= n_simulations

        results["avg_total_goals"] = sum(results["total_goals"]) / n_simulations
        results["over_2_5"] = sum(1 for g in results["total_goals"] if g > 2) / n_simulations

        return results


# 兼容不同Python版本的Poisson抽样
def _poisson_variate(lambda_: float) -> int:
    """生成一个Poisson随机数（不使用random.poissonvariate）"""
    if lambda_ <= 0:
        return 0
    L = math.exp(-lambda_)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1

# 替换random.poissonvariate（3.8+有，但确保兼容）
random.poissonvariate = getattr(random, 'poissonvariate', _poisson_variate)


class EloRating:
    """
    Elo 动态评分系统

    用于动态评估球队实力变化，每场比赛后更新评分。
    比静态的攻防参数更能反映球队的实时状态。
    """

    def __init__(self, k_factor: int = 30):
        """
        参数:
            k_factor: Elo K值，越大则评分变化越剧烈
                      - 世界杯建议: 30-40
                      - 联赛建议: 20-30
        """
        self.k_factor = k_factor
        self.ratings: Dict[str, float] = {}

    def set_rating(self, team: str, rating: float):
        self.ratings[team] = rating

    def get_rating(self, team: str, default: float = 1500.0) -> float:
        return self.ratings.get(team, default)

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """计算A队对B队的预期得分 (0-1)"""
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def update(
        self,
        team_a: str,
        team_b: str,
        score_a: int,
        score_b: int,
        margin_factor: float = 1.0
    ):
        """
        比赛后更新 Elo 评分

        净胜球影响: 赢1球 margin_factor=1, 赢3球 margin_factor=1.5
        """
        rating_a = self.get_rating(team_a)
        rating_b = self.get_rating(team_b)

        expected_a = self.expected_score(rating_a, rating_b)

        # 实际得分 (1=赢, 0.5=平, 0=输)
        if score_a > score_b:
            actual_a = 1.0
        elif score_a == score_b:
            actual_a = 0.5
        else:
            actual_a = 0.0

        # 净胜球系数
        goal_diff = abs(score_a - score_b)
        goal_diff_factor = 1.0 + (goal_diff - 1) * 0.1 * margin_factor
        goal_diff_factor = min(goal_diff_factor, 2.0)  # 上限2倍

        # 更新评分
        new_rating_a = rating_a + self.k_factor * goal_diff_factor * (actual_a - expected_a)
        new_rating_b = rating_b + self.k_factor * goal_diff_factor * (expected_a - actual_a)

        self.ratings[team_a] = new_rating_a
        self.ratings[team_b] = new_rating_b
