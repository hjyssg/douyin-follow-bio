"""
抖音关注列表个人简介批量获取工具
使用 Playwright 控制系统 Chrome，通过拦截网络请求自动获取关注列表数据。
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# 配置
SEC_USER_ID = "MS4wLjABAAAAzHkg47DBc1iWLuoCYkxARcOPnf-cibgzdxnu0iXUxK8"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 漫展相关关键词
KEYWORDS = [
    "漫展", "CP", "BW", "CJ", "COMICUP", "签售", "返图", "约拍", "约片",
    "行程", "场照", "coser", "cos", "出cos", "摊位", "同人展",
    "萤火虫", "国际动漫节", "IDO", "CICF", "AGF", "CCG", "XYCC",
    "魔都同人祭", "广州", "上海", "北京", "成都", "杭州", "深圳",
    "南京", "武汉", "重庆", "长沙",
]

all_followings = []
seen_uids = set()


def on_response(response):
    """拦截关注列表 API 响应"""
    url = response.url
    if "user/following/list" not in url:
        return
    try:
        data = response.json()
        if data.get("status_code") != 0:
            return
        followings = data.get("followings", [])
        for user in followings:
            uid = user.get("uid", "")
            if uid in seen_uids:
                continue
            seen_uids.add(uid)
            all_followings.append({
                "nickname": user.get("nickname", ""),
                "signature": user.get("signature", ""),
                "uid": uid,
                "sec_uid": user.get("sec_uid", ""),
                "follower_count": user.get("follower_count", 0),
                "unique_id": user.get("unique_id", ""),
            })
        print(f"  [拦截] 获取到 {len(followings)} 个用户，累计去重 {len(all_followings)} 个")
    except Exception as e:
        print(f"  [拦截] 解析响应失败: {e}")


def save_results():
    """保存结果到文件"""
    print(f"\n共获取 {len(all_followings)} 个关注用户")

    if not all_followings:
        print("没有获取到任何数据，请检查是否正确登录并滚动了页面。")
        return

    # 保存完整 JSON
    full_path = OUTPUT_DIR / "all_followings.json"
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(all_followings, f, ensure_ascii=False, indent=2)
    print(f"完整数据已保存到: {full_path}")

    # 生成简介汇总
    summary_path = OUTPUT_DIR / "bio_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"抖音关注列表简介汇总 (共 {len(all_followings)} 人)\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        for i, user in enumerate(all_followings, 1):
            f.write(f"[{i}] {user['nickname']}\n")
            sig = user["signature"].strip() if user["signature"] else "(无简介)"
            f.write(f"    简介: {sig}\n")
            f.write(f"    粉丝: {user['follower_count']}\n")
            f.write(f"    主页: https://www.douyin.com/user/{user['sec_uid']}\n\n")
    print(f"简介汇总已保存到: {summary_path}")

    # 过滤漫展行程
    filtered = []
    for user in all_followings:
        sig = (user.get("signature") or "").lower()
        nickname = (user.get("nickname") or "").lower()
        text = sig + " " + nickname
        matched = [kw for kw in KEYWORDS if kw.lower() in text]
        if matched:
            filtered.append({**user, "matched_keywords": matched})

    event_path = OUTPUT_DIR / "coser_events.txt"
    with open(event_path, "w", encoding="utf-8") as f:
        f.write(f"可能包含漫展/行程信息的用户 (共 {len(filtered)} 人)\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        for i, user in enumerate(filtered, 1):
            f.write(f"[{i}] {user['nickname']}\n")
            sig = user["signature"].strip() if user["signature"] else "(无简介)"
            f.write(f"    简介: {sig}\n")
            f.write(f"    匹配关键词: {', '.join(user['matched_keywords'])}\n")
            f.write(f"    主页: https://www.douyin.com/user/{user['sec_uid']}\n\n")
    print(f"漫展行程筛选结果已保存到: {event_path}")
    print(f"  共 {len(filtered)} 人的简介中包含漫展相关关键词")
    print("\n完成！")


def main():
    print("=" * 60)
    print("抖音关注列表个人简介批量获取工具")
    print("=" * 60)
    print()
    print("使用方法：")
    print("1. 浏览器打开后，请先登录抖音（如果未登录）")
    print("2. 登录后按回车，脚本会自动跳转到你的关注页面")
    print("3. 请手动向下滚动页面，加载更多关注用户")
    print("4. 脚本会自动拦截 API 响应并收集数据")
    print("5. 滚动到底部后，回到终端按回车保存结果")
    print()

    with sync_playwright() as p:
        user_data_dir = str(Path(__file__).parent / "chrome_profile")
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            channel="chrome",
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()

        # 注册响应拦截
        page.on("response", on_response)

        # 先打开抖音让用户登录
        page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
        input("\n>>> 请在浏览器中登录抖音，登录完成后回到这里按回车继续...")

        # 跳转到关注页面
        follow_url = f"https://www.douyin.com/user/{SEC_USER_ID}?showTab=following"
        print(f"\n正在跳转到关注页面...")
        page.goto(follow_url, wait_until="domcontentloaded")
        time.sleep(3)

        print(f"\n当前已拦截到 {len(all_followings)} 个用户")
        print("请在浏览器中不断向下滚动，加载所有关注用户。")
        print("脚本会自动拦截数据，你可以在终端看到进度。")
        input("\n>>> 滚动到底部后，回到这里按回车保存结果...")

        context.close()

    save_results()


if __name__ == "__main__":
    main()
