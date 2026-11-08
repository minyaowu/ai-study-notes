"""Record a real before/after content extension and verify shared code hashes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
from build import ROOT, load_topics, render_site


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot():
    output, topics = render_site()
    shared_paths = [ROOT / "AGENTS.md", ROOT / "project.json"]
    for name in ("templates", "assets", "schemas", "scripts"):
        shared_paths.extend(p for p in (ROOT / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return {
        "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "topics": [t["slug"] for t in topics],
        "card_count": sum(len(t["cards"]) for t in topics),
        "shared_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sorted(shared_paths)},
        "content_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sorted((ROOT / "content").glob("*.json"))},
        "generated_sha256": {k: digest(v) for k, v in output.items()},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    phase = parser.parse_args().phase
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    destination = evidence / (phase + ".json")
    if destination.exists():
        raise SystemExit("Evidence already exists; preserve the original record")
    state = snapshot()
    if phase == "before":
        destination.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"phase":phase,"topics":len(state["topics"]),"cards":state["card_count"]}))
        return
    before = json.loads((evidence / "before.json").read_text(encoding="utf-8"))
    added = sorted(set(state["topics"]) - set(before["topics"]))
    changed_shared = sorted(k for k in state["shared_sha256"].keys() | before["shared_sha256"].keys()
                            if state["shared_sha256"].get(k) != before["shared_sha256"].get(k))
    changed_content = sorted(k for k in state["content_sha256"].keys() | before["content_sha256"].keys()
                             if state["content_sha256"].get(k) != before["content_sha256"].get(k))
    changed_generated = sorted(k for k in state["generated_sha256"].keys() | before["generated_sha256"].keys()
                               if state["generated_sha256"].get(k) != before["generated_sha256"].get(k))
    if len(added) != 1 or changed_shared or len(changed_content) != 1:
        raise SystemExit("Extension contract not met: expected one new content file and unchanged shared sources")
    state["verification"] = {"added_topics":added,"changed_shared_files":changed_shared,
                             "changed_content_files":changed_content,"changed_generated_files":changed_generated}
    destination.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 依 AGENTS.md 新增主題：實作紀錄", "",
        "本次由同一位 AI 助理實際依 AGENTS.md 與內容範例操作，保存前後 SHA-256 指紋，沒有宣稱另一位 AI 已獨立測試。", "",
        "## 新增任務", "",
        "請依 AGENTS.md 新增「AI 幻覺與資訊查核」主題，使用既有格式、版型與翻卡功能，完成三張附原文依據的卡片。", "",
        "## 實際結果", "",
        f"- 新增前：{len(before['topics'])} 個主題，{before['card_count']} 張卡。",
        f"- 新增後：{len(state['topics'])} 個主題，{state['card_count']} 張卡。",
        "- 只新增一份內容檔：" + changed_content[0],
        "- 共用規則、版型、樣式、前端程式、建置程式與 schema 的 SHA-256 在本次操作前後相同。",
        "- 首頁、主題頁、前後篇導覽及複習卡由建置程式更新。", "",
        "## 自動產生的檔案差異", "",
    ] + ["- docs/" + name for name in changed_generated] + [
        "", "## 如何重現下一次新增", "",
        "閱讀 AGENTS.md 與 templates/topic.example.json，新增 content/<new-slug>.json，執行：", "",
        "~~~text", "python scripts/build.py", "python scripts/build.py --check",
        "python -m unittest discover -s tests -v", "~~~", "",
        "再於首頁、主題頁與複習頁確認內容和來源。若只是新增合規內容，不必新增專屬版型或修改共用 JavaScript。", "",
        "## 證據的範圍", "",
        "before.json 與 after.json 記錄的是這次新增操作，不是保證任何 AI 未來都能零錯誤完成。問答語意、外部來源與最終呈現仍須檢查。後續發布網址設定會更新 project.json，與本次新增內容實驗分開。", "",
    ]
    (evidence / "extension-demo.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(state["verification"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
