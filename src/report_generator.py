"""
Customer Analysis Report Generator
===================================
Generates professional customer-facing prediction reports for betting tips.
Optimized for mobile screenshot sharing on WeChat.

Output: HTML (screenshot-friendly, 420px mobile card)
"""
import math
from typing import Dict, Optional, Any, List, Tuple
from src.poisson_model import PredictionResult, TeamStrength


class ReportGenerator:
    """Generate professional betting tips reports for customer sharing."""

    def generate_customer_html(
        self,
        result: PredictionResult,
        home_team: Optional[TeamStrength] = None,
        away_team: Optional[TeamStrength] = None,
    ) -> str:
        """Generate a complete customer-facing report HTML (mobile-optimized)."""
        return self._build_report(result, home_team, away_team)

    def _build_report(self, result, home_team, away_team):
        ht = result.home_team
        at = result.away_team
        hwp = round(result.home_win_prob * 100, 1)
        dwp = round(result.draw_prob * 100, 1)
        awp = round(result.away_win_prob * 100, 1)
        ml = result.most_likely_score
        conf = round(result.confidence * 100, 1)
        cl = result.confidence_label()
        rec_type, rec_label = self._get_recommendation(hwp, dwp, awp, ht, at)
        rec_color = {"home": "var(--accent2)", "away": "var(--danger)", "draw": "var(--warn)"}.get(rec_type, "var(--accent2)")
        scores_html = "".join(self._score_row(h, a, p, max(4, p * 200)) for (h, a), p in result.top_scores(10))
        tg_html = "".join(self._tg_row(k, v, max(4, v * 250)) for k, v in result.total_goals_chinese.items())
        ou = result.over_under
        over_pct = ou.get("over", 0) * 100
        under_pct = ou.get("under", 0) * 100
        ou_rec = chr(22823)+chr(29699) if over_pct >= under_pct else chr(23567)+chr(29699)
        ou_bar_over = max(4, over_pct * 2.5)
        ou_bar_under = max(4, under_pct * 2.5)
        btts_pct = result.btts["both_teams_to_score"]
        btts_rec = chr(26159) if btts_pct >= 50 else chr(21542)
        ts_html = self._team_strength_rows(ht, at, home_team, away_team) if home_team and away_team else ""
        analysis = self._generate_analysis_cn(result, home_team, away_team)
        exp_goals = result.lambda_home + result.lambda_away
        ht_letter = ht[0].upper()
        at_letter = at[0].upper()
        hr = f"FIFA #{home_team.fifa_ranking}" if home_team else "?"
        he = f"Elo {home_team.elo_rating:.0f}" if home_team else "?"
        ar = f"FIFA #{away_team.fifa_ranking}" if away_team else "?"
        ae = f"Elo {away_team.elo_rating:.0f}" if away_team else "?"
        ccolor = "var(--success)" if conf >= 70 else ("var(--warn)" if conf >= 50 else "var(--danger)")
        return self._build_html(ht, at, hwp, dwp, awp, ml, conf, cl,
            rec_type, rec_label, rec_color,
            scores_html, tg_html, over_pct, under_pct, ou_rec,
            ou_bar_over, ou_bar_under,
            btts_pct, btts_rec, ts_html, analysis, exp_goals,
            ht_letter, at_letter, hr, he, ar, ae, ccolor)

    def _build_html(self, ht, at, hwp, dwp, awp, ml, conf, cl,
                    rec_type, rec_label, rec_color,
                    scores_html, tg_html, over_pct, under_pct, ou_rec,
                    ou_bar_over, ou_bar_under,
                    btts_pct, btts_rec, ts_html, analysis, exp_goals,
                    ht_letter, at_letter, home_rank, home_elo, away_rank, away_elo, ccolor):
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>预测报告 - {ht} vs {at}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#0a0e27;--card:#141833;--border:#2a2f4a;--text:#e0e0e0;--dim:#889;
--accent:#7b2ff7;--accent2:#00d4ff;--success:#00d48a;--danger:#ff6b6b;--warn:#ffd700;
--grad:linear-gradient(135deg,#00d4ff,#7b2ff7)}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",sans-serif;background:var(--bg);color:var(--text)}}
.report{{max-width:420px;margin:0 auto;padding:12px}}
.header{{text-align:center;padding:24px 12px 16px;position:relative}}
.match-teams{{display:flex;align-items:center;justify-content:center;gap:16px}}
.team-badge{{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:1.3em;margin:0 auto 6px}}
.rec-card{{background:var(--grad);border-radius:12px;padding:16px;text-align:center;margin:16px 0;position:relative}}
.rec-label{{font-size:.7em;opacity:.8;margin-bottom:4px}}
.rec-value{{font-size:1.6em;font-weight:800;letter-spacing:2px}}
.rec-odds{{font-size:.85em;opacity:.8;margin-top:4px}}
.rec-conf{{position:absolute;top:8px;right:10px;font-size:.65em;opacity:.6}}
.section{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:10px}}
.section-title{{font-size:.82em;font-weight:600;color:var(--accent2);margin-bottom:10px}}
.wdw-bar{{display:flex;height:10px;border-radius:5px;overflow:hidden;margin:8px 0}}
.wdw-home{{background:var(--accent2)}}
.wdw-draw{{background:var(--warn)}}
.wdw-away{{background:var(--danger)}}
.wdw-labels{{display:flex;justify-content:space-between;font-size:.75em;color:var(--dim)}}
.wdw-labels span{{text-align:center;flex:1}}
.bet-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:.85em}}
.bet-row:last-child{{border:none}}
.bet-label{{color:var(--dim)}}
.bet-value{{font-weight:600}}
.c-home{{color:var(--accent2)}}
.c-away{{color:var(--danger)}}
.c-draw{{color:var(--warn)}}
.c-yes{{color:var(--success)}}
.footer{{text-align:center;padding:20px 0;font-size:.65em;color:var(--dim)}}
</style>
</head><body><div class="report">

<div class="header">
    <div class="match-teams">
        <div style="text-align:center">
            <div class="team-badge" style="background:var(--accent)">{ht_letter}</div>
            <div style="font-size:.9em;font-weight:600">{ht}</div>
            <div style="font-size:.7em;color:var(--dim)">{home_rank} | {home_elo}</div>
        </div>
        <div class="vs-text">VS</div>
        <div style="text-align:center">
            <div class="team-badge" style="background:var(--accent2)">{at_letter}</div>
            <div style="font-size:.9em;font-weight:600">{at}</div>
            <div style="font-size:.7em;color:var(--dim)">{away_rank} | {away_elo}</div>
        </div>
    </div>
</div>

<div class="rec-card">
    <div class="rec-label">推 荐</div>
    <div class="rec-value" style="color:{rec_color}">{rec_label}</div>
    <div class="rec-odds">主 {hwp}% &nbsp;平 {dwp}% &nbsp;客 {awp}%</div>
    <div class="rec-conf">信心 {conf}%</div>
</div>

<div class="section">
    <div class="section-title">胜平负概率</div>
    <div class="wdw-bar"><div class="wdw-home" style="width:{max(1,hwp)}%"></div><div class="wdw-draw" style="width:{max(1,dwp)}%"></div><div class="wdw-away" style="width:{max(1,awp)}%"></div></div>
    <div class="wdw-labels"><span>主胜 {hwp}%</span><span>平局 {dwp}%</span><span>客胜 {awp}%</span></div>
</div>

<div class="section">
    <div class="section-title">比分概率 (Top 10)</div>
    {scores_html}
</div>

<div class="section">
    <div class="section-title">总进球分布</div>
    {tg_html}
    <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;font-size:.82em">
            <span>大球 ({ou_rec}) <span style="color:var(--success);font-weight:600">{over_pct:.1f}%</span></span>
            <span>小球 <span style="color:var(--danger);font-weight:600">{under_pct:.1f}%</span></span>
        </div>
        <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;margin-top:4px">
            <div style="width:{ou_bar_over:.0f}%;background:var(--success)"></div>
            <div style="width:{ou_bar_under:.0f}%;background:var(--danger)"></div>
        </div>
    </div>
</div>

<div class="section">
    <div class="section-title">双方进球 (BTTS)</div>
    <div style="display:flex;align-items:center;gap:12px">
        <div style="flex:1;height:8px;background:rgba(255,255,255,.06);border-radius:4px;overflow:hidden">
            <div style="height:100%;width:{btts_pct:.0f}%;background:var(--grad);border-radius:4px"></div>
        </div>
        <span style="font-size:1.1em;font-weight:700">{btts_pct:.1f}%</span>
    </div>
    <div style="font-size:.78em;color:var(--dim);margin-top:4px">推荐: <span style="color:{"var(--success)" if btts_rec == "是" else "var(--danger)"};font-weight:600">{btts_rec}</span></div>
</div>

<div class="section">
    <div class="section-title">竞猜推荐</div>
    <div class="bet-row"><span class="bet-label">胜平负</span><span class="bet-value c-{rec_type}">{rec_label}</span></div>
    <div class="bet-row"><span class="bet-label">比分推荐</span><span class="bet-value" style="color:var(--accent2)">{ml[0]}-{ml[1]}</span></div>
    <div class="bet-row"><span class="bet-label">总进球</span><span class="bet-value" style="color:var(--success)">{ou_rec} ({exp_goals:.2f})</span></div>
    <div class="bet-row"><span class="bet-label">双方进球</span><span class="bet-value" style="color:{"var(--success)" if btts_rec == "是" else "var(--danger)"}">{btts_rec}</span></div>
    <div class="bet-row"><span class="bet-label">信心指数</span><span class="bet-value" style="color:{ccolor}">{cl} ({conf}%)</span></div>
</div>

<div class="section">
    <div class="section-title">实力对比</div>
    <div style="display:flex;justify-content:space-between;font-size:.7em;color:var(--dim);margin-bottom:6px">
        <span>{ht}</span><span>{at}</span>
    </div>
    {ts_html}
</div>

<div class="section">
    <div class="section-title">分析</div>
    <div style="font-size:.82em;line-height:1.8">{analysis}</div>
</div>

<div class="footer">
    <div>2026 World Cup Prediction</div>
    <div style="margin-top:4px">AI 分析仅供参考</div>
</div>

</div></body></html>"""

    def _score_row(self, h, a, p, bar_w):
        return f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">\n    <span style="width:80px;font-size:.82em;text-align:right">{h}-{a}</span>\n    <div style="flex:1;height:6px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden">\n        <div style="height:100%;width:{bar_w:.0f}%;background:linear-gradient(90deg,#00d4ff,#7b2ff7);border-radius:3px"></div>\n    </div>\n    <span style="width:45px;font-size:.78em;color:var(--dim);text-align:right">{p*100:.1f}%</span>\n</div>'

    def _tg_row(self, k, v, bar_w):
        return f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">\n    <span style="width:50px;font-size:.78em;text-align:right">{k}</span>\n    <div style="flex:1;height:5px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden">\n        <div style="height:100%;width:{bar_w:.0f}%;background:var(--accent2);border-radius:3px"></div>\n    </div>\n    <span style="width:40px;font-size:.72em;color:var(--dim);text-align:right">{v:.1f}%</span>\n</div>'

    def _team_strength_rows(self, ht, at, home_team, away_team):
        rows = ""
        items = [
            ("攻击", home_team.attack, away_team.attack, None),
            ("防守", home_team.defense, away_team.defense, "invert"),
            ("Elo", home_team.elo_rating / 2000, away_team.elo_rating / 2000, None),
            ("状态", home_team.recent_form / 1.2, away_team.recent_form / 1.2, None),
            ("士气", home_team.morale / 1.2, away_team.morale / 1.2, None),
        ]
        for label, hv, av, mode in items:
            if mode == "invert" and hv > 0 and av > 0:
                h_bar = min(2.0 / hv * 50, 100)
                a_bar = min(2.0 / av * 50, 100)
            elif max(av, hv) > 0:
                m = max(av, hv)
                h_bar = min(hv / m * 100, 100)
                a_bar = min(av / m * 100, 100)
            else:
                h_bar = a_bar = 50
            rows += f"""<div style="margin-bottom:8px">
    <div style="display:flex;justify-content:space-between;font-size:.72em;color:var(--dim);margin-bottom:2px">
        <span>{label}</span>
        <span style="color:var(--accent2)">{hv:.3f}</span>
        <span style="color:var(--danger)">{av:.3f}</span>
    </div>
    <div style="display:flex;gap:2px;height:6px">
        <div style="flex:1;background:rgba(0,212,255,.15);border-radius:3px 0 0 3px;overflow:hidden">
            <div style="height:100%;width:{h_bar:.0f}%;background:var(--accent2);border-radius:3px 0 0 3px"></div>
        </div>
        <div style="flex:1;background:rgba(255,107,107,.15);border-radius:0 3px 3px 0;overflow:hidden">
            <div style="height:100%;width:{a_bar:.0f}%;background:var(--danger);border-radius:0 3px 3px 0"></div>
        </div>
    </div>
</div>"""
        return rows

    def _get_recommendation(self, hwp, dwp, awp, ht, at):
        if hwp >= 55:
            return ("home", f"主胜 {ht}")
        if hwp >= 45 and dwp >= 28:
            return ("home", f"主不败 {ht}")
        if awp >= 55:
            return ("away", f"客胜 {at}")
        if awp >= 45 and dwp >= 28:
            return ("away", f"客不败 {at}")
        if dwp >= 35:
            return ("draw", "平局")
        return ("home", f"双选 {ht}或平")

    def _generate_analysis_cn(self, result, home_team, away_team):
        lines = []
        ht = result.home_team
        at = result.away_team
        lg = result.lambda_home
        la = result.lambda_away
        lines.append(f"本场由 {ht} 对阵 {at}。")
        if lg > 1.5:
            lines.append(f"{ht} 预期进球 {lg:.2f}，攻击力强劲。")
        elif lg < 0.8:
            lines.append(f"{ht} 预期进球 {lg:.2f}，进攻火力有限。")
        else:
            lines.append(f"{ht} 预期进球 {lg:.2f}，进攻表现稳定。")
        if la > 1.5:
            lines.append(f"{at} 预期进球 {la:.2f}，攻击力强劲。")
        elif la < 0.8:
            lines.append(f"{at} 预期进球 {la:.2f}，进攻火力有限。")
        else:
            lines.append(f"{at} 预期进球 {la:.2f}，进攻表现稳定。")
        if home_team and away_team:
            if home_team.attack > away_team.attack * 1.15:
                lines.append(f"{ht} 攻击力明显强于 {at}。")
            elif away_team.attack > home_team.attack * 1.15:
                lines.append(f"{at} 攻击力明显强于 {ht}。")
            else:
                lines.append("双方攻击力较为接近。")
        if result.home_win_prob >= 0.65:
            lines.append(f"模型显示 {ht} 胜率较高 ({result.home_win_prob*100:.0f}%)，看好主胜。")
        elif result.away_win_prob >= 0.65:
            lines.append(f"模型显示 {at} 胜率较高 ({result.away_win_prob*100:.0f}%)，看好客胜。")
        elif result.draw_prob >= 0.30:
            lines.append(f"平局概率 {result.draw_prob*100:.0f}%，需防平局。")
        elif result.home_win_prob >= 0.50:
            lines.append(f"{ht} 稍占优势 ({result.home_win_prob*100:.0f}%)，主队不败可期。")
        elif result.away_win_prob >= 0.50:
            lines.append(f"{at} 稍占优势 ({result.away_win_prob*100:.0f}%)，客队不败可期。")
        te = lg + la
        if te >= 3.0:
            lines.append(f"总预期进球 {te:.2f}，看好大球方向。")
        elif te <= 1.8:
            lines.append(f"总预期进球 {te:.2f}，倾向小球方向。")
        else:
            lines.append(f"总预期进球 {te:.2f}，大小球均有可能。")
        bv = result.btts["both_teams_to_score"]
        if bv >= 60:
            lines.append(f"双方进球概率 {bv:.0f}%，看好两队都能破门。")
        elif bv <= 35:
            lines.append(f"双方进球概率 {bv:.0f}%，至少一方可能被零封。")
        return "".join(f"<p style='margin-bottom:6px'>{l}</p>" for l in lines)

    def generate_html(self, result, home_team=None, away_team=None):
        return self.generate_customer_html(result, home_team, away_team)

    def generate_json(self, result, home_team=None, away_team=None):
        return {
            "home_team": result.home_team,
            "away_team": result.away_team,
            "expected_goals": {"home": round(result.lambda_home, 2), "away": round(result.lambda_away, 2)},
            "win_draw_win": result.win_draw_win_formatted(),
            "most_likely_score": "%d-%d" % result.most_likely_score,
            "top_scores": result.top_scores_formatted(10),
            "total_goals": dict(result.total_goals_chinese),
            "over_under": dict(result.over_under),
            "btts": result.btts,
            "confidence": result.confidence_label(),
        }

    def generate_json_output(self, result, home_team=None, away_team=None):
        cj = result.cjklottery_format
        return {
            "match_id": result.home_team[:3].upper() + "-" + result.away_team[:3].upper(),
            "home_team": result.home_team,
            "away_team": result.away_team,
            "expected_goals": {"home": round(result.lambda_home, 2), "away": round(result.lambda_away, 2)},
            "win_draw_win": {"home_win": round(result.home_win_prob * 100, 1), "draw": round(result.draw_prob * 100, 1), "away_win": round(result.away_win_prob * 100, 1)},
            "most_likely_score": {"%d-%d" % result.most_likely_score: round(result.score_probabilities[result.most_likely_score] * 100, 1)},
            "top_scores": {"%d-%d" % (h, a): round(p * 100, 1) for (h, a), p in result.top_scores(10)},
            "total_goals": dict(result.total_goals_chinese),
            "over_under": dict(result.over_under),
            "btts": {"both": result.btts["both_teams_to_score"]},
            "confidence": round(result.confidence * 100, 1),
        }