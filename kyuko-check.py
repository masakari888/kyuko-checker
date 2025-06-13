import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from collections import defaultdict
import os
import sys

def fetch_kyuko_text():
    url = "https://portal.shuchiin.ac.jp/"
    try:
        response = requests.get(url, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")
        p_tag = soup.select_one("#login-infomation p")
        return p_tag.get_text(separator="\n", strip=True) if p_tag else ""
    except requests.exceptions.RequestException as e:
        print(f"❌ スクレイピングエラー: {e}")
        return ""

def normalize_kyuko_lines(text):
    lines = text.split("\n")
    lines = [line.strip().replace("\u00a0", " ") for line in lines if line.strip()]
    current_date = None
    normalized = []
    date_pattern = re.compile(r"(\d{1,2})月(\d{1,2})日\(.+?\)")

    for line in lines:
        match = date_pattern.search(line)
        if match:
            current_date = f"{int(match.group(1)):02d}-{int(match.group(2)):02d}"
            normalized.append((current_date, line))
        elif current_date:
            normalized.append((current_date, line))
    return normalized

def extract_period(line):
    match = re.search(r"第(\d)講時", line)
    return int(match.group(1)) if match else 99

def group_and_sort_by_date(lines):
    grouped = defaultdict(list)
    for date, line in lines:
        grouped[date].append(line)

    sorted_grouped = {}
    for date, line_list in grouped.items():
        sorted_lines = sorted(line_list, key=extract_period)
        sorted_grouped[date] = sorted_lines
    return sorted_grouped

def save_as_json(data, filename="kyuko_info.json"):
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": today,
            "data": data
        }, f, ensure_ascii=False, indent=2)

def format_message(data):
    if not data:
        return "📢 現在、休講情報はありません。"

    lines = ["📢 休講情報"]
    for date, items in sorted(data.items()):
        lines.append(f"\n📅 {date.replace('-', '/')}：")
        for item in items:
            lines.append(f"・{item}")
    return "\n".join(lines)

def send_line_notify(message: str):
    token = os.getenv("LINE_NOTIFY_TOKEN")
    if not token:
        print("⚠️ LINE_NOTIFY_TOKEN が設定されていません")
        return

    res = requests.post(
        "https://notify-api.line.me/api/notify",
        headers={"Authorization": f"Bearer {token}"},
        data={"message": message}
    )
    if res.status_code == 200:
        print("✅ LINE通知送信完了")
    else:
        print(f"❌ LINE通知失敗: {res.status_code} - {res.text}")

def main():
    print("✅ スクリプト開始")
    raw = fetch_kyuko_text()
    if not raw:
        print("⚠️ 休講情報の取得に失敗")
        sys.exit(1)

    print("✅ データ取得成功")
    normalized = normalize_kyuko_lines(raw)
    grouped = group_and_sort_by_date(normalized)
    save_as_json(grouped)
    print("✅ JSON保存完了")
    msg = format_message(grouped)
    print("✅ メッセージ整形完了")
    send_line_notify(msg)
    print("✅ スクリプト終了")
    sys.exit(0)

if __name__ == "__main__":
    main()
