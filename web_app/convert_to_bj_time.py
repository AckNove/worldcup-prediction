# -*- coding: utf-8 -*-
"""
将WC2026赛程时间从UTC转换为北京时间（UTC+8）
"""

import json
from datetime import datetime, timedelta

# 读取原始赛程数据
with open('wc2026_schedule.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取WC2026_SCHEDULE = [...] 部分
# 先找到开始和结束位置
start_marker = "WC2026_SCHEDULE = ["
start_idx = content.find(start_marker)
if start_idx == -1:
    print("未找到WC2026_SCHEDULE")
    exit(1)

# 找到匹配的结束方括号
start_list = start_idx + len(start_marker) - 1  # 包含[
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
    exit(1)

# 提取列表内容
list_content = content[start_list:end_idx + 1]

# 使用exec执行来获取数据
local_vars = {}
exec(f"WC2026_SCHEDULE = {list_content}", globals(), local_vars)
schedule = local_vars['WC2026_SCHEDULE']

print(f"总比赛数: {len(schedule)}")
print()
print("转换前（前5场）:")
for m in schedule[:5]:
    print(f"  {m['date']} {m['time']} - {m['home']} vs {m['away']}")

# 转换时间：UTC + 8小时 = 北京时间
converted = []
for m in schedule:
    # 解析时间
    date_str = m['date']
    time_str = m['time']
    
    # 创建datetime对象
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    
    # 加8小时
    dt_bj = dt + timedelta(hours=8)
    
    # 转换回字符串
    new_date = dt_bj.strftime("%Y-%m-%d")
    new_time = dt_bj.strftime("%H:%M")
    
    converted_m = m.copy()
    converted_m['date'] = new_date
    converted_m['time'] = new_time
    converted.append(converted_m)

print()
print("转换后（前5场）:")
for m in converted[:5]:
    print(f"  {m['date']} {m['time']} - {m['home']} vs {m['away']}")

# 重新生成Python文件内容
new_schedule_str = "WC2026_SCHEDULE = [\n"
for i, m in enumerate(converted):
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
    if i < len(converted) - 1:
        new_schedule_str += ","
    new_schedule_str += "\n"
new_schedule_str += "]\n"

# 替换原文件中的WC2026_SCHEDULE部分
new_content = content[:start_idx] + new_schedule_str + content[end_idx + 1:]

# 备份原文件
import shutil
shutil.copy('wc2026_schedule.py', 'wc2026_schedule.py.backup_utc')

# 写入新文件
with open('wc2026_schedule.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print()
print(f"✅ 已转换 {len(converted)} 场比赛时间为北京时间")
print(f"✅ 原文件已备份为 wc2026_schedule.py.backup_utc")
print(f"✅ 新文件已写入 wc2026_schedule.py")
