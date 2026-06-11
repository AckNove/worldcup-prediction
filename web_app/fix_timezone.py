# -*- coding: utf-8 -*-
"""
修正2026世界杯赛程时间时区问题

根据用户反馈：
- 当前显示：墨西哥vs南非 6月11日19:00
- 用户期望：墨西哥vs南非 6月12日03:00北京时间

分析：
当前时间是 2026-06-11 19:00
期望时间是 2026-06-12 03:00
时差：+8小时

让我们直接调整所有比赛时间 +8小时
"""

import json
import shutil
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

SOURCE_FILE = 'wc2026_schedule.py'
JSON_FILE = 'data/schedule.json'
BACKUP_FILE = 'wc2026_schedule.py.backup_before_fix'

def load_schedule():
    """从Python文件加载赛程数据"""
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    start_marker = "WC2026_SCHEDULE = ["
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("未找到WC2026_SCHEDULE")
        return None, None, None

    start_list = start_idx + len(start_marker) - 1
    bracket_count = 0
    end_idx = -1
    in_string = False
    string_char = None
    i = start_list

    while i < len(content):
        c = content[i]
        if in_string:
            if c == '\\' and i + 1 < len(content):
                i += 2
                continue
            if c == string_char:
                in_string = False
            i += 1
            continue

        if c == '"' or c == "'":
            in_string = True
            string_char = c
            i += 1
            continue

        if c == '[':
            bracket_count += 1
        elif c == ']':
            bracket_count -= 1
            if bracket_count == 0:
                end_idx = i
                break
        i += 1

    if end_idx == -1:
        print("未找到结束括号")
        return None, None, None

    list_content = content[start_list:end_idx + 1]

    local_vars = {}
    exec(f"WC2026_SCHEDULE = {list_content}", globals(), local_vars)
    schedule = local_vars['WC2026_SCHEDULE']

    ko_start = content.find("KNOCKOUT_SCHEDULE = [")
    knockout = []
    ko_end_idx = -1
    if ko_start != -1:
        ko_start_list = ko_start + len("KNOCKOUT_SCHEDULE = [") - 1
        bracket_count = 0
        in_string = False
        string_char = None
        i = ko_start_list
        while i < len(content):
            c = content[i]
            if in_string:
                if c == '\\' and i + 1 < len(content):
                    i += 2
                    continue
                if c == string_char:
                    in_string = False
                i += 1
                continue
            if c == '"' or c == "'":
                in_string = True
                string_char = c
                i += 1
                continue
            if c == '[':
                bracket_count += 1
            elif c == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    ko_end_idx = i
                    break
            i += 1
        if ko_end_idx != -1:
            ko_list_content = content[ko_start_list:ko_end_idx + 1]
            exec(f"KNOCKOUT_SCHEDULE = {ko_list_content}", globals(), local_vars)
            knockout = local_vars.get('KNOCKOUT_SCHEDULE', [])

    return schedule, knockout, (content, start_idx, end_idx, ko_start, ko_end_idx)

def convert_match(match, offset_hours):
    """转换比赛时间"""
    date_str = match['date']
    time_str = match['time']

    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    dt_bj = dt + timedelta(hours=offset_hours)

    new_match = match.copy()
    new_match['date'] = dt_bj.strftime("%Y-%m-%d")
    new_match['time'] = dt_bj.strftime("%H:%M")

    return new_match

def main():
    print("=" * 60)
    print("修正2026世界杯赛程时区问题")
    print("=" * 60)
    print()

    schedule, knockout, content_info = load_schedule()
    if schedule is None:
        print("错误：无法加载赛程数据")
        return

    print(f"小组赛: {len(schedule)} 场")
    print(f"淘汰赛: {len(knockout)} 场")
    print()

    first_match = schedule[0]
    print("当前首场比赛:")
    print(f"  {first_match['home']} vs {first_match['away']}")
    print(f"  当前显示: {first_match['date']} {first_match['time']}")
    print(f"  地点: {first_match['city']}")
    print()

    print("根据您的反馈:")
    print("  期望显示: 2026-06-12 03:00")
    print("  需要增加: +8小时")
    print()

    offset = 8

    shutil.copy(SOURCE_FILE, BACKUP_FILE)
    print(f"原文件已备份到: {BACKUP_FILE}")
    print()

    converted_schedule = [convert_match(m, offset) for m in schedule]
    converted_knockout = [convert_match(m, offset) for m in knockout]

    first_converted = converted_schedule[0]
    print("转换后首场比赛:")
    print(f"  {first_converted['date']} {first_converted['time']} - {first_converted['home']} vs {first_converted['away']}")
    if first_converted['date'] == "2026-06-12" and first_converted['time'] == "03:00":
        print("  OK: 匹配期望时间")
    print()

    print("前5场比赛转换后:")
    for i, m in enumerate(converted_schedule[:5]):
        print(f"  {i+1}. {m['date']} {m['time']} - {m['home']} vs {m['away']}")
    print()

    content, start_idx, end_idx, ko_start, ko_end_idx = content_info

    new_schedule_str = "WC2026_SCHEDULE = [\n"
    for i, m in enumerate(converted_schedule):
        new_schedule_str += "    {\n"
        new_schedule_str += f'        "date": "{m["date"]}",\n'
        new_schedule_str += f'        "time": "{m["time"]}",\n'
        new_schedule_str += f'        "home": "{m["home"]}",\n'
        new_schedule_str += f'        "away": "{m["away"]}",\n'
        new_schedule_str += f'        "venue": "{m["venue"]}",\n'
        new_schedule_str += f'        "city": "{m["city"]}",\n'
        new_schedule_str += f'        "round": "{m["round"]}",\n'
        new_schedule_str += f'        "fixture_id": {m["fixture_id"]},\n'
        new_schedule_str += f'        "status": "{m["status"]}",\n'
        new_schedule_str += f'        "home_score": {m["home_score"]},\n'
        new_schedule_str += f'        "away_score": {m["away_score"]},\n'
        new_schedule_str += "    }"
        if i < len(converted_schedule) - 1:
            new_schedule_str += ","
        new_schedule_str += "\n"
    new_schedule_str += "]\n"

    new_ko_str = "KNOCKOUT_SCHEDULE = [\n"
    for i, m in enumerate(converted_knockout):
        new_ko_str += "    {\n"
        new_ko_str += f'        "date": "{m["date"]}",\n'
        new_ko_str += f'        "time": "{m["time"]}",\n'
        new_ko_str += f'        "home": "{m["home"]}",\n'
        new_ko_str += f'        "away": "{m["away"]}",\n'
        new_ko_str += f'        "venue": "{m["venue"]}",\n'
        new_ko_str += f'        "city": "{m["city"]}",\n'
        new_ko_str += f'        "round": "{m["round"]}",\n'
        new_ko_str += f'        "fixture_id": {m["fixture_id"]},\n'
        new_ko_str += f'        "status": "{m["status"]}",\n'
        new_ko_str += f'        "home_score": {m["home_score"]},\n'
        new_ko_str += f'        "away_score": {m["away_score"]},\n'
        new_ko_str += "    }"
        if i < len(converted_knockout) - 1:
            new_ko_str += ","
        new_ko_str += "\n"
    new_ko_str += "]\n"

    new_content = content[:start_idx] + new_schedule_str + content[end_idx + 1:]

    ko_start_new = new_content.find("KNOCKOUT_SCHEDULE = [")
    if ko_start_new != -1:
        ko_start_list = ko_start_new + len("KNOCKOUT_SCHEDULE = [") - 1
        bracket_count = 0
        ko_end_idx_new = -1
        in_string = False
        string_char = None
        i = ko_start_list
        while i < len(new_content):
            c = new_content[i]
            if in_string:
                if c == '\\' and i + 1 < len(new_content):
                    i += 2
                    continue
                if c == string_char:
                    in_string = False
                i += 1
                continue
            if c == '"' or c == "'":
                in_string = True
                string_char = c
                i += 1
                continue
            if c == '[':
                bracket_count += 1
            elif c == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    ko_end_idx_new = i
                    break
            i += 1

        if ko_end_idx_new != -1:
            new_content = new_content[:ko_start_new] + new_ko_str + new_content[ko_end_idx_new + 1:]

    with open(SOURCE_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"已更新: {SOURCE_FILE}")

    all_matches = converted_schedule + converted_knockout
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_matches, f, indent=2, ensure_ascii=False)
    print(f"已更新: {JSON_FILE}")

    print()
    print("=" * 60)
    print("时区修正完成！")
    print("=" * 60)
    print("首场比赛:")
    print(f"  墨西哥 vs 南非")
    print(f"  北京时间: {first_converted['date']} {first_converted['time']}")
    print()
    print("请重启服务器以应用更改。")


if __name__ == "__main__":
    main()
