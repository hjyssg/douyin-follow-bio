"""
解析关注列表简介，提取漫展/线下行程信息。

可被 fetch_followings.py 直接调用，也可单独运行：
  python parse_bio.py
"""
import io
import json
import re
import sys
from pathlib import Path

# Windows 终端 GBK 编码兼容
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUTPUT_DIR = Path(__file__).parent / "output"

# ── 漫展/行程相关关键词 ──
SCHEDULE_KEYWORDS = [
    "漫展", "签售", "萤火虫", "only", "fes", "嘉年华", "快闪",
    "世界线", "次元", "动漫", "摄影会", "一日店长", "签赠",
    "GameFes", "ComicFes", "ICG", "IDO", "CP展", "BW", "CJ",
    "SSCA", "IJOY", "WF展", "FC展", "ACG", "DC", "mars",
    "NewEra", "冲击波", "梦乡", "梦幻星",
    "行程", "✈️", "🌟程", "线下",
]


def has_schedule_info(signature: str) -> bool:
    """判断简介是否包含行程信息"""
    if not signature or signature == "(无简介)":
        return False
    sig_lower = signature.lower()
    for kw in SCHEDULE_KEYWORDS:
        if kw.lower() in sig_lower:
            return True
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
        if re.search(r'\d{1,2}[./]\d{1,2}', line) and re.search(r'[\u4e00-\u9fff]', line):
            result.append(line)
        elif any(kw.lower() in line.lower() for kw in ["行程", "线下", "签售", "漫展"]):
            result.append(line)
    return result


def parse_and_print(users: list):
    """解析用户列表，在终端打印行程汇总"""
    schedule_users = [u for u in users if has_schedule_info(u.get("signature", ""))]

    print(f"\n{'='*60}")
    print(f"  漫展/行程信息筛选: {len(schedule_users)} / {len(users)} 人")
    print(f"{'='*60}\n")

    for i, u in enumerate(schedule_users, 1):
        nickname = u["nickname"]
        sig = u.get("signature", "")
        fans = u.get("follower_count", 0)
        schedule_lines = extract_schedule_lines(sig)

        fans_str = f"{fans/10000:.1f}w" if fans >= 10000 else str(fans)
        print(f"[{i}] {nickname}  ({fans_str}粉)")

        if schedule_lines:
            for line in schedule_lines:
                print(f"    > {line}")
        else:
            short_sig = sig.replace("\n", " ")[:100]
            print(f"    * {short_sig}")
        print()

    print(f"{'='*60}")
    print(f"共 {len(schedule_users)} 人含行程信息")
    print(f"{'='*60}")


def _find_latest_data():
    """找到 output/ 下最新日期目录中的 all_followings.json"""
    if not OUTPUT_DIR.exists():
        return None
    # 按目录名倒序找最新的日期目录
    date_dirs = sorted(
        [d for d in OUTPUT_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    for d in date_dirs:
        json_path = d / "all_followings.json"
        if json_path.exists():
            return json_path
    # fallback: output/all_followings.json（旧格式兼容）
    fallback = OUTPUT_DIR / "all_followings.json"
    if fallback.exists():
        return fallback
    return None


def main():
    json_path = _find_latest_data()
    if json_path is None:
        print("错误：找不到 all_followings.json，请先运行 fetch_followings.py")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        users = json.load(f)

    print(f"数据来源: {json_path} ({len(users)} 人)")
    parse_and_print(users)


if __name__ == "__main__":
    main()
