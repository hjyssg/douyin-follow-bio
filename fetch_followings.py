r"""
抖音关注列表个人简介批量获取工具
连接到 Chrome 浏览器（调试模式），监听关注列表 API 响应。

使用方法：
1. 运行本脚本：python fetch_followings.py
2. 脚本会自动关闭所有 Chrome 并用调试模式重启
3. 在 Chrome 中登录抖音、打开关注列表、滚动加载
4. 回到终端按回车保存结果
"""
import json
import time
import subprocess
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# 配置
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
CDP_URL = "http://127.0.0.1:9222"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

all_followings = []
seen_uids = set()
raw_responses = []
request_count = 0


def kill_all_chrome():
    """杀掉所有 Chrome 进程"""
    print("正在关闭所有 Chrome 进程...")
    os.system("taskkill /F /IM chrome.exe >nul 2>&1")
    time.sleep(2)


def start_chrome_debug():
    """用调试模式启动 Chrome"""
    user_data = str(Path(__file__).parent / "chrome_debug_profile")
    cmd = [
        CHROME_PATH,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    print("正在启动 Chrome (调试模式)...")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(15):
        time.sleep(1)
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2)
            data = json.loads(resp.read())
            print(f"  Chrome 已启动: {data.get('Browser', 'unknown')}")
            return True
        except Exception:
            if i < 14:
                print(f"  等待 Chrome 启动... ({i+1}s)")
    return False


def main():
    global request_count

    print("=" * 60)
    print("  抖音关注列表个人简介批量获取工具")
    print("=" * 60)
    print()

    kill_all_chrome()
    if not start_chrome_debug():
        print("\nChrome 启动失败！")
        return

    print()
    print("正在连接 Chrome...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"\n连接 Chrome 失败: {e}")
            return

        print(f"已连接到 Chrome (共 {len(browser.contexts)} 个 context)")

        context = browser.contexts[0] if browser.contexts else None
        if not context:
            print("没有找到浏览器 context")
            return

        print(f"当前有 {len(context.pages)} 个标签页")

        # 用 CDP session 直接监听网络事件，不干扰正常请求
        page = context.pages[0] if context.pages else context.new_page()
        cdp = context.new_cdp_session(page)

        # 启用网络监听
        cdp.send("Network.enable")

        # 存储待处理的响应
        pending_bodies = {}

        def on_response_received(params):
            """CDP Network.responseReceived 事件"""
            url = params.get("response", {}).get("url", "")
            if "following/list" in url or "following_list" in url:
                request_id = params.get("requestId")
                pending_bodies[request_id] = url

        def on_loading_finished(params):
            """CDP Network.loadingFinished 事件 - 响应体已就绪"""
            global request_count
            request_id = params.get("requestId")
            if request_id not in pending_bodies:
                return

            url = pending_bodies.pop(request_id)
            try:
                result = cdp.send("Network.getResponseBody", {"requestId": request_id})
                body_str = result.get("body", "")
                if result.get("base64Encoded"):
                    import base64
                    body_str = base64.b64decode(body_str).decode("utf-8")

                data = json.loads(body_str)
                request_count += 1
                raw_responses.append(data)

                if data.get("status_code") != 0:
                    print(f"  [监听 #{request_count}] API status_code={data.get('status_code')}")
                    return

                followings = data.get("followings")
                if followings and isinstance(followings, list):
                    new_count = 0
                    for user in followings:
                        uid = user.get("uid")
                        if not uid or uid in seen_uids:
                            continue
                        seen_uids.add(uid)
                        new_count += 1
                        all_followings.append({
                            "nickname": user.get("nickname", ""),
                            "signature": user.get("signature", ""),
                            "uid": uid,
                            "sec_uid": user.get("sec_uid", ""),
                            "follower_count": user.get("follower_count", 0),
                            "unique_id": user.get("unique_id", ""),
                        })

                    total = data.get("total", "?")
                    has_more = data.get("has_more", False)
                    print(f"\n  ✅ [捕获 #{request_count}] +{new_count} 新用户 (本页{len(followings)}条) | 累计: {len(all_followings)}/{total} | {'还有更多' if has_more else '已到底'}")

                    # 在 Chrome 页面上弹一个通知，让你知道捕获到了
                    try:
                        page.evaluate(f"document.title = '✅ 已捕获 {len(all_followings)}/{total} 个关注'")
                    except BaseException:
                        pass

            except Exception as e:
                print(f"  [监听] 读取响应体失败: {type(e).__name__}: {e}")

        cdp.on("Network.responseReceived", on_response_received)
        cdp.on("Network.loadingFinished", on_loading_finished)

        print()
        print("=" * 60)
        print("监听已就绪！请在 Chrome 中操作：")
        print("  1. 打开 https://www.douyin.com/ 并登录")
        print("  2. 进入你的个人主页")
        print("  3. 点击「关注」打开关注列表弹窗")
        print("  4. 在弹窗中不断向下滚动，加载所有关注")
        print("=" * 60)
        print("\n终端会实时显示监听到的数据...\n")

        try:
            input(">>> 滚动完成后按回车保存结果...")
        except (KeyboardInterrupt, EOFError):
            print("\n中断，保存已有数据...")

        try:
            cdp.detach()
        except Exception:
            pass

    save_results()


def save_results():
    """保存结果到文件"""
    print(f"\n{'='*60}")
    print(f"共监听到 {request_count} 次请求，{len(all_followings)} 个去重用户")

    if raw_responses:
        raw_path = OUTPUT_DIR / "raw_responses.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_responses, f, ensure_ascii=False, indent=2)
        print(f"原始响应 → {raw_path} ({len(raw_responses)} 条)")

    if not all_followings:
        print("\n没有获取到用户数据。")
        print("排查建议：")
        print("  1. 在 Chrome 中按 F12 → Network 面板")
        print("  2. 在关注列表弹窗中滚动")
        print("  3. 看 Network 中是否有 following/list 请求")
        print("  4. 把实际 URL 告诉我")
        return

    full_path = OUTPUT_DIR / "all_followings.json"
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(all_followings, f, ensure_ascii=False, indent=2)
    print(f"用户数据 → {full_path}")

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
    print(f"简介汇总 → {summary_path}")

    print("\n完成！")


if __name__ == "__main__":
    main()
