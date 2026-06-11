"""
Prediction Data Scheduler
==========================
Runs periodic data refresh cycles in a background thread.

Cycle (every UPDATE_INTERVAL hours):
  1. Fetch completed match results from API
  2. Update Elo/form/morale via DataManager
  3. Fetch player stats from recent matches
  4. Recompute player states → team strengths
  5. Save all state to disk

Designed to be started as a daemon thread from web_app/server.py.
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from .api_client import ApiFootballClient, get_api_client
from .team_integrator import get_team_integrator

# How often to run the full refresh cycle (in hours)
UPDATE_INTERVAL = 2

# How far back to look for recent results (in days)
RESULTS_LOOKBACK = 3

# Data directory for status tracking
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'web_app', 'data')


class PredictionScheduler:
    """Background scheduler for periodic data refresh."""

    def __init__(self, data_manager, update_interval: int = UPDATE_INTERVAL):
        self.data_manager = data_manager
        self.update_interval = update_interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._force_refresh = False

        # Status tracking
        self.last_cycle_start = 0.0
        self.last_cycle_end = 0.0
        self.cycle_count = 0
        self.last_error = ""
        self.is_running_now = False

        # API call stats for this session
        self.api_calls = 0

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    def start(self, api_key: str = None):
        """Start the background scheduler thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="prediction-scheduler")
        self._thread.start()

        client = get_api_client(api_key)
        if client.is_configured():
            print(f"  [Scheduler] API key configured, background updates every {self.update_interval}h")
        else:
            print(f"  [Scheduler] No API key — running in offline mode")

    def stop(self):
        """Stop the scheduler."""
        self._running = False

    def request_refresh(self):
        """Request an immediate refresh (non-blocking)."""
        self._force_refresh = True

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    def _run_loop(self):
        """Main scheduler loop."""
        # Run initial refresh after short delay
        time.sleep(5)
        self._execute_cycle()

        # Periodic refresh loop
        while self._running:
            # Wait, but check every 30 seconds for force_refresh
            waited = 0
            while waited < self.update_interval * 3600:
                if not self._running:
                    return
                if self._force_refresh:
                    self._force_refresh = False
                    break
                time.sleep(30)
                waited += 30

            self._execute_cycle()

    # ------------------------------------------------------------------
# Execute Cycle
# ------------------------------------------------------------------

    def _execute_cycle(self):
        """Execute one full refresh cycle."""
        self.is_running_now = True
        self.last_cycle_start = time.time()
        self.cycle_count += 1
        cycle_num = self.cycle_count

        print(f"\n{'='*50}")
        print(f"  [Scheduler] Cycle #{cycle_num} starting...")
        print(f"{'='*50}")

        try:
            # Step 1: Fetch recent match results from API
            self._step_fetch_results()

            # Step 2: Refresh team integrator (player states → team strength)
            self._step_refresh_integrator()

            # Step 3: Fetch and update schedule
            self._step_fetch_schedule()

            # Step 4: Fetch warmup friendlies
            self._step_fetch_warmup()

            # Step 5: Save state
            self._step_save()

            self.last_cycle_end = time.time()
            duration = round(self.last_cycle_end - self.last_cycle_start, 1)
            print(f"  [Scheduler] Cycle #{cycle_num} complete ({duration}s)")
            self.last_error = ""

        except Exception as e:
            self.last_error = str(e)
            print(f"  [Scheduler] Cycle #{cycle_num} error: {e}")

        self.is_running_now = False

    def _step_fetch_results(self):
        """Step 1: Fetch recent match results from API and update DataManager."""
        client = get_api_client()

        if not client.is_configured():
            print(f"  [Scheduler]  No API key — skipping result fetch")
            return

        print(f"  [Scheduler] 1/5 Fetching recent results...")

        # Get recent completed matches
        results = client.get_recent_results(days_back=RESULTS_LOOKBACK)
        self.api_calls += 1

        api_results = 0
        new_results = 0

        for fixture in results:
            fixture_data = fixture.get("fixture", {})
            fixture_id = fixture_data.get("id", 0)
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})

            home_team_info = teams.get("home", {})
            away_team_info = teams.get("away", {})

            api_home = home_team_info.get("name", "")
            api_away = away_team_info.get("name", "")

            home_goals = goals.get("home")
            away_goals = goals.get("away")

            if home_goals is None or away_goals is None:
                continue

            api_results += 1

            # Map API names to internal names
            from .team_integrator import TeamIntegrator
            home = TeamIntegrator._map_team_name(api_home)
            away = TeamIntegrator._map_team_name(api_away)

            if not home or not away:
                continue

            # Check if already recorded (avoid duplicates)
            existing = self.data_manager.match_history
            already = any(
                m.get("home") == home and m.get("away") == away
                and m.get("home_goals") == home_goals
                and m.get("away_goals") == away_goals
                for m in existing[-20:]
            )

            if not already:
                try:
                    self.data_manager.add_match_result(home, away, home_goals, away_goals)
                    new_results += 1
                    print(f"  [Scheduler]   Result: {home} {home_goals}-{away_goals} {away}")
                except Exception as e:
                    print(f"  [Scheduler]   Error recording {home} vs {away}: {e}")

        print(f"  [Scheduler]  Fetched {api_results} results, {new_results} new")

    def _step_refresh_integrator(self):
        """Step 2: Refresh all player and team computations."""
        print(f"  [Scheduler] 2/5 Refreshing player states & team strengths...")

        integrator = get_team_integrator(self.data_manager)
        integrator.refresh_all()

        print(f"  [Scheduler]  Done — {len(integrator.squad_data)} teams, "
              f"{sum(len(v) for v in integrator.squad_data.values())} players")

    def _step_fetch_schedule(self):
        """Step 3: Fetch 2026 World Cup schedule from API and save to JSON."""
        client = get_api_client()

        if not client.is_configured():
            print(f"  [Scheduler]  No API key — skipping schedule fetch")
            return

        print(f"  [Scheduler] 3/5 Fetching 2026 World Cup schedule...")

        try:
            # Fetch all 2026 World Cup matches from API
            # League ID 1 = World Cup, Season 2026
            params = {"league": 1, "season": 2026}
            response = client._request("/fixtures", params)

            if not response or not isinstance(response, list):
                print(f"  [Scheduler]  No schedule data from API")
                return

            print(f"  [Scheduler]  Fetched {len(response)} fixtures from API")

            # Convert API data to our format
            schedule = []
            for fixture in response:
                fixture_data = fixture.get("fixture", {})
                teams = fixture.get("teams", {})
                goals = fixture.get("goals", {})
                score = fixture.get("score", {})

                home_team = teams.get("home", {}).get("name", "")
                away_team = teams.get("away", {}).get("name", "")

                # Skip if missing team names
                if not home_team or not away_team:
                    continue

                # Get fixture date and time
                fixture_date = fixture_data.get("date", "")[:10]  # YYYY-MM-DD
                fixture_time = fixture_data.get("date", "")[11:16]  # HH:MM

                # Get venue
                venue = fixture_data.get("venue", {})
                venue_name = venue.get("name", "")
                venue_city = venue.get("city", "")

                # Get status
                status = fixture_data.get("status", {})
                status_short = status.get("short", "")
                status_text = "已结束" if status_short == "FT" else "未开始"

                # Get scores
                home_score = goals.get("home")
                away_score = goals.get("away")

                # Determine round
                round_info = fixture_data.get("round", {})
                round_str = round_info.get("name", "小组赛")

                schedule.append({
                    "date": fixture_date,
                    "time": fixture_time,
                    "home": home_team,
                    "away": away_team,
                    "venue": venue_name,
                    "city": venue_city,
                    "round": round_str,
                    "fixture_id": fixture_data.get("id", 0),
                    "status": status_text,
                    "home_score": home_score,
                    "away_score": away_score,
                })

            # Save to JSON file
            schedule_file = os.path.join(DATA_DIR, "schedule.json")
            with open(schedule_file, "w", encoding="utf-8") as f:
                json.dump(schedule, f, ensure_ascii=False, indent=2)

            print(f"  [Scheduler]  Schedule saved to {schedule_file} ({len(schedule)} matches)")

        except Exception as e:
            print(f"  [Scheduler]  Error fetching schedule: {e}")

    def _step_fetch_warmup(self):
        """Step 4: Fetch warmup friendlies for WC teams and save to JSON.
        Friendlies have league_id=10 in API-Football."""
        client = get_api_client()

        if not client.is_configured():
            print(f"  [Scheduler]  No API key — skipping warmup fetch")
            return

        print(f"  [Scheduler] 4/5 Fetching warmup friendlies...")

        try:
            # Get WC team IDs from API
            wc_teams = client.get_teams()
            self.api_calls += 1
            if not wc_teams:
                print(f"  [Scheduler]  No WC teams from API")
                return

            id_to_name = {}
            for t in wc_teams:
                info = t.get("team", {})
                id_to_name[info.get("id", 0)] = info.get("name", "")

            # Date range: May 1 - June 10 (before WC starts June 11)
            warmup_start = "2026-05-01"
            warmup_end = "2026-06-10"
            today_str = datetime.now().strftime("%Y-%m-%d")

            # If WC already started, skip warmup fetch
            if today_str > warmup_end:
                print(f"  [Scheduler]  WC already started, skipping warmup fetch")
                return

            seen = set()
            all_warmup = []

            for tid in sorted(id_to_name.keys()):
                try:
                    data = client._request("/fixtures", {
                        "team": tid,
                        "last": "10",
                        "timezone": "Asia/Shanghai"
                    })
                    self.api_calls += 1

                    if data and "response" in data:
                        for r in data["response"]:
                            f = r.get("fixture", {})
                            fid = f.get("id", 0)
                            league = r.get("league", {})
                            lid = league.get("id", 0)

                            if lid != 10:  # Only Friendlies
                                continue

                            fdate = f.get("date", "")[:10]
                            if fdate < warmup_start or fdate > warmup_end:
                                continue

                            if fid not in seen:
                                seen.add(fid)
                                teams = r.get("teams", {})
                                home = teams.get("home", {})
                                away = teams.get("away", {})
                                goals = r.get("goals", {})
                                status_short = f.get("status", {}).get("short", "")
                                venue_raw = f.get("venue", {})
                                if isinstance(venue_raw, dict):
                                    venue_name = venue_raw.get("name", "")
                                else:
                                    venue_name = str(venue_raw) if venue_raw else ""

                                all_warmup.append({
                                    "fixture_id": fid,
                                    "date": fdate,
                                    "time": f.get("date", "")[11:16],
                                    "home": home.get("name", ""),
                                    "away": away.get("name", ""),
                                    "home_score": goals.get("home"),
                                    "away_score": goals.get("away"),
                                    "status": "已结束" if status_short == "FT" else "进行中" if status_short in ("LIVE", "HT", "ET", "P", "BT") else "未开始",
                                    "venue": venue_name,
                                })

                    time.sleep(1.1)
                except Exception as e:
                    print(f"  [Scheduler]  Error for team {tid}: {e}")

            all_warmup.sort(key=lambda x: (x["date"], x["time"]))

            # Save to JSON
            warmup_file = os.path.join(DATA_DIR, "warmup_schedule.json")
            with open(warmup_file, "w", encoding="utf-8") as f:
                json.dump(all_warmup, f, ensure_ascii=False, indent=2)

            print(f"  [Scheduler]  Warmup saved: {len(all_warmup)} friendlies")

            # Also regenerate warmup_data.py for server import
            warmup_py = os.path.join(os.path.dirname(__file__), "..", "web_app", "warmup_data.py")
            with open(warmup_py, "w", encoding="utf-8") as f:
                f.write('"""\n2026世界杯热身赛数据（从API-Football实时获取）\n所有时间均为北京时间（UTC+8）\n自动更新于：' + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n\"\"\"\n\nWARMUP_MATCHES = [\n")
                for m in all_warmup:
                    f.write("    {\n")
                    f.write(f'        "date": "{m["date"]}",\n')
                    f.write(f'        "time": "{m["time"]}",\n')
                    f.write(f'        "home": "{m["home"]}",\n')
                    f.write(f'        "away": "{m["away"]}",\n')
                    f.write(f'        "venue": "{m["venue"]}",\n')
                    if m["home_score"] is not None:
                        f.write(f'        "home_score": {m["home_score"]},\n')
                        f.write(f'        "away_score": {m["away_score"]},\n')
                    else:
                        f.write(f'        "home_score": None,\n')
                        f.write(f'        "away_score": None,\n')
                    f.write(f'        "status": "{m["status"]}",\n')
                    f.write(f'        "fixture_id": {m["fixture_id"]},\n')
                    f.write("    },\n")
                f.write("]\n")

            print(f"  [Scheduler]  warmup_data.py regenerated")

        except Exception as e:
            print(f"  [Scheduler]  Error fetching warmup: {e}")

    def _step_save(self):
        """Step 5: Save all state to disk."""
        print(f"  [Scheduler] 5/5 Saving state...")
        # DataManager already auto-saves in add_match_result()
        # TeamIntegrator saves during refresh_all()
        print(f"  [Scheduler]  State saved")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Get scheduler status for admin display."""
        now = time.time()
        hours_since = (now - self.last_cycle_end) / 3600 if self.last_cycle_end else 999

        next_run = ""
        if self.last_cycle_end:
            next_time = self.last_cycle_end + self.update_interval * 3600
            try:
                next_run = datetime.fromtimestamp(next_time).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        return {
            "is_running": self.is_running_now,
            "is_alive": self._running,
            "cycle_count": self.cycle_count,
            "last_cycle_start": datetime.fromtimestamp(self.last_cycle_start).strftime("%Y-%m-%d %H:%M:%S") if self.last_cycle_start else "Never",
            "last_cycle_end": datetime.fromtimestamp(self.last_cycle_end).strftime("%Y-%m-%d %H:%M:%S") if self.last_cycle_end else "Never",
            "hours_since_update": round(hours_since, 1),
            "next_scheduled": next_run,
            "update_interval_hours": self.update_interval,
            "last_error": self.last_error,
            "api_calls_session": self.api_calls,
            "api_configured": get_api_client().is_configured(),
        }


# ============================================================================
# Singleton
# ============================================================================

_scheduler_instance = None


def get_scheduler(data_manager=None) -> PredictionScheduler:
    """Get or create the singleton scheduler."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = PredictionScheduler(data_manager)
    return _scheduler_instance


def start_scheduler(data_manager, api_key: str = None):
    """Convenience: create and start the scheduler."""
    sched = get_scheduler(data_manager)
    sched.start(api_key)
    return sched
