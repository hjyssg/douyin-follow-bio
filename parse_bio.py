"""
解析 bio_summary.txt，提取关注列表中的漫展/线下行程信息。

功能：
1. 从 bio_summary.txt 或 all_followings.json 解析用户数据
2. 用关键词匹配提取含行程信息的用户
3. 输出行程汇总（按日期排序）

用法：
  python parse_bio.py              # 解析并输出行程汇总
  python parse_bio.py --all        # 输出所有用户（含无行程的）
  python parse_bio.py --json       # 输出 JSON 格式
  python parse_bio.py --prompt     # 生成 LLM prompt，用 AI 提取结构化行程
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent / "output"

# ── 漫展/行程相关关键词 ──
SCHEDULE_KEYWORDS = [
    # 漫展/活动名
    "漫展", "签售", "萤火虫", "only", "fes", "嘉年华", "快闪",
    "世界线", "次元", "动漫", "摄影会", "一日店长", "签赠",
    "GameFes", "ComicFes", "ICG", "IDO", "CP展", "BW", "CJ",
    "SSCA", "IJOY", "WF展", "FC展", "ACG", "DC", "mars",
    "NewEra", "冲击波", "梦乡", "梦幻星",
    # 行程相关
    "行程", "✈️", "🌟程", "线下",
    # 日期模式（月.日 或 月/日）
]

# 日期正则：匹配 1.24, 2/8, 12.26-28 等
DATE_PATTERN = re.compile(
    r'(\d{1,2})[./](\d{1,2})(?:\s*[-~]\s*\d{1,2})?(?:\s*[-~]\s*(\d{1,2})[./](\d{1,2}))?'
)


def load_from_json():
    """从 all_followings.json 加载"""
    json_path = OUTPUT_DIR / "all_followings.json"
    if not json_path.exists():
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_from_txt():
    """从 bio_summary.txt 解析"""
    txt_path = OUTPUT_DIR / "bio_summary.txt"
    if not txt_path.exists():
        return None

    users = []
    current = None
    sig_lines = []

    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            # 匹配 [序号] 昵称
            m = re.match(r'^\[(\d+)\]\s+(.+)$', line)
            if m:
                if current:
                    current["signature"] = "\n".join(sig_lines).strip()
                    users.append(current)
                current = {
                    "index": int(m.group(1)),
                    "nickname": m.group(2).strip(),
                    "signature": "",
                    "follower_count": 0,
                    "sec_uid": "",
                }
                sig_lines = []
                continue

            if current is None:
                continue

            # 匹配简介行
            if line.startswith("    简介: "):
                sig_lines.append(line[len("    简介: "):])
            elif line.startswith("    粉丝: "):
                try:
                    current["follower_count"] = int(line[len("    粉丝: "):].strip())
                except ValueError:
                    pass
            elif line.startswith("    主页: "):
                url = line[len("    主页: "):].strip()
                # 提取 sec_uid
                if "/user/" in url:
                    current["sec_uid"] = url.split("/user/")[-1]
            elif line.startswith("    ") and sig_lines:
                # 多行简介的续行
                sig_lines.append(line.strip())

    if current:
        current["signature"] = "\n".join(sig_lines).strip()
        users.append(current)

    return users


def has_schedule_info(signature: str) -> bool:
    """判断简介是否包含行程信息"""
    if not signature or signature == "(无简介)":
        return False

    sig_lower = signature.lower()

    # 关键词匹配
    for kw in SCHEDULE_KEYWORDS:
        if kw.lower() in sig_lower:
            return True

    # 日期+地点模式：如 "2.8深圳" "1.1上海"
    if re.search(r'\d{1,2}[./]\d{1,2}\s*[\u4e00-\u9fff]', signature):
        return True

    return False


def extract_schedule_lines(signature: str) -> list[str]:
    """从简介中提取行程相关的行"""
    if not signature:
        return []

    lines = signature.replace("｜", "\n").replace("|", "\n").split("\n")
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 包含日期+地点的行
        if re.search(r'\d{1,2}[./]\d{1,2}', line) and re.search(r'[\u4e00-\u9fff]', line):
            result.append(line)
        elif any(kw.lower() in line.lower() for kw in ["行程", "线下", "签售", "漫展"]):
            result.append(line)
    return result


def classify_user(signature: str) -> str:
    """简单分类用户类型"""
    if not signature or signature == "(无简介)":
        return "未知"

    sig = signature.lower()
    categories = []

    if any(kw in sig for kw in ["coser", "cos", "cosplay", "三坑", "lolita", "汉服", "jk"]):
        categories.append("Coser/三坑")
    if any(kw in sig for kw in ["摄影", "约拍", "拍摄"]):
        categories.append("摄影师")
    if any(kw in sig for kw in ["主播", "直播"]):
        categories.append("主播")
    if any(kw in sig for kw in ["游戏", "电竞", "ow", "守望", "原神", "崩坏"]):
        categories.append("游戏")
    if any(kw in sig for kw in ["投资", "交易", "金融", "基金", "财经"]):
        categories.append("财经")
    if any(kw in sig for kw in ["官方", "官号"]):
        categories.append("官方号")
    if any(kw in sig for kw in ["表情包", "原创角色", "ip"]):
        categories.append("IP/表情包")

    return "/".join(categories) if categories else "其他"


def generate_llm_prompt(users: list) -> str:
    """生成给 LLM 的 prompt，让 AI 提取结构化行程数据"""
    # 只取有行程信息的用户
    schedule_users = [u for u in users if has_schedule_info(u.get("signature", ""))]

    prompt = """你是一个数据提取助手。以下是抖音用户的个人简介，请从中提取所有漫展/线下活动行程信息。

要求：
1. 提取每条行程的：日期、城市、活动名称、活动类型（签售/漫展/快闪/商演/其他）
2. 日期格式统一为 YYYY-MM-DD（年份默认2026，如果月份已过则为2025）
3. 如果日期是范围（如1.1-1.3），拆成起止日期
4. 输出 JSON 数组格式

示例输出：
```json
[
  {
    "nickname": "xxx",
    "events": [
      {
        "date_start": "2026-02-08",
        "date_end": "2026-02-08",
        "city": "深圳",
        "event_name": "AL迎春之约",
        "type": "签售"
      }
    ]
  }
]
```

以下是用户数据：
"""
    for u in schedule_users:
        prompt += f"\n---\n昵称: {u['nickname']}\n简介: {u.get('signature', '')}\n"

    prompt += "\n---\n请提取所有行程信息，输出 JSON。"
    return prompt


def main():
    args = set(sys.argv[1:])

    # 优先从 JSON 加载，否则从 TXT 解析
    users = load_from_json()
    source = "all_followings.json"
    if users is None:
        users = load_from_txt()
        source = "bio_summary.txt"
    if users is None:
        print("错误：找不到 output/all_followings.json 或 output/bio_summary.txt")
        sys.exit(1)

    print(f"数据来源: {source} ({len(users)} 人)")
    print()

    # ── 模式：生成 LLM prompt ──
    if "--prompt" in args:
        prompt = generate_llm_prompt(users)
        prompt_path = OUTPUT_DIR / "extract_schedule_prompt.txt"
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"LLM Prompt 已保存到: {prompt_path}")
        print(f"字数: {len(prompt)}")
        print("\n你可以把这个 prompt 粘贴给 ChatGPT/Claude 来提取结构化行程数据。")
        return

    # ── 提取有行程的用户 ──
    schedule_users = []
    no_schedule_users = []

    for u in users:
        sig = u.get("signature", "")
        if has_schedule_info(sig):
            schedule_users.append(u)
        else:
            no_schedule_users.append(u)

    # ── 模式：JSON 输出 ──
    if "--json" in args:
        output = []
        for u in schedule_users:
            output.append({
                "nickname": u["nickname"],
                "signature": u.get("signature", ""),
                "follower_count": u.get("follower_count", 0),
                "category": classify_user(u.get("signature", "")),
                "schedule_lines": extract_schedule_lines(u.get("signature", "")),
                "profile_url": f"https://www.douyin.com/user/{u.get('sec_uid', '')}",
            })
        json_path = OUTPUT_DIR / "schedule_users.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"含行程用户 JSON 已保存到: {json_path} ({len(output)} 人)")
        return

    # ── 默认模式：行程汇总 ──
    print(f"{'='*60}")
    print(f"  含行程/漫展信息的用户: {len(schedule_users)} / {len(users)}")
    print(f"{'='*60}\n")

    for i, u in enumerate(schedule_users, 1):
        nickname = u["nickname"]
        sig = u.get("signature", "")
        fans = u.get("follower_count", 0)
        category = classify_user(sig)
        schedule_lines = extract_schedule_lines(sig)

        fans_str = f"{fans/10000:.1f}w" if fans >= 10000 else str(fans)
        print(f"[{i}] {nickname}  ({fans_str}粉)  [{category}]")

        if schedule_lines:
            for line in schedule_lines:
                print(f"    📅 {line}")
        else:
            # 没提取到具体行，打印完整简介的前100字
            short_sig = sig.replace("\n", " ")[:100]
            print(f"    📝 {short_sig}")
        print()

    # ── 统计 ──
    print(f"\n{'='*60}")
    print("分类统计:")
    cat_count = {}
    for u in users:
        cat = classify_user(u.get("signature", ""))
        cat_count[cat] = cat_count.get(cat, 0) + 1
    for cat, count in sorted(cat_count.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # ── --all 模式额外输出 ──
    if "--all" in args:
        print(f"\n\n{'='*60}")
        print(f"  无行程信息的用户 ({len(no_schedule_users)} 人)")
        print(f"{'='*60}\n")
        for u in no_schedule_users:
            sig = u.get("signature", "").replace("\n", " ")[:60]
            print(f"  {u['nickname']}: {sig or '(无简介)'}")

    # 保存行程汇总
    summary_path = OUTPUT_DIR / "schedule_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"漫展/线下行程汇总 (从 {len(users)} 人中筛选)\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"含行程信息: {len(schedule_users)} 人\n")
        f.write("=" * 60 + "\n\n")
        for i, u in enumerate(schedule_users, 1):
            nickname = u["nickname"]
            sig = u.get("signature", "")
            fans = u.get("follower_count", 0)
            schedule_lines = extract_schedule_lines(sig)
            fans_str = f"{fans/10000:.1f}w" if fans >= 10000 else str(fans)
            f.write(f"[{i}] {nickname}  ({fans_str}粉)\n")
            if schedule_lines:
                for line in schedule_lines:
                    f.write(f"    📅 {line}\n")
            else:
                short_sig = sig.replace("\n", " ")[:120]
                f.write(f"    📝 {short_sig}\n")
            f.write(f"    🔗 https://www.douyin.com/user/{u.get('sec_uid', '')}\n\n")

    print(f"\n行程汇总已保存到: {summary_path}")


if __name__ == "__main__":
    main()
