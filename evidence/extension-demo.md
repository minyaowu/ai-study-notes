# 依 AGENTS.md 新增主題：實作紀錄

本次由同一位 AI 助理實際依 AGENTS.md 與內容範例操作，保存前後 SHA-256 指紋，沒有宣稱另一位 AI 已獨立測試。

## 新增任務

請依 AGENTS.md 新增「AI 幻覺與資訊查核」主題，使用既有格式、版型與翻卡功能，完成三張附原文依據的卡片。

## 實際結果

- 新增前：2 個主題，6 張卡。
- 新增後：3 個主題，9 張卡。
- 只新增一份內容檔：content/hallucination-checking.json
- 共用規則、版型、樣式、前端程式、建置程式與 schema 的 SHA-256 在本次操作前後相同。
- 首頁、主題頁、前後篇導覽及複習卡由建置程式更新。

## 自動產生的檔案差異

- docs/about.html
- docs/data/cards.json
- docs/index.html
- docs/review.html
- docs/topics/generative-ai.html
- docs/topics/hallucination-checking.html
- docs/topics/prompt-design.html

## 如何重現下一次新增

閱讀 AGENTS.md 與 templates/topic.example.json，新增 content/<new-slug>.json，執行：

~~~text
python scripts/build.py
python scripts/build.py --check
python -m unittest discover -s tests -v
~~~

再於首頁、主題頁與複習頁確認內容和來源。若只是新增合規內容，不必新增專屬版型或修改共用 JavaScript。

## 證據的範圍

before.json 與 after.json 記錄的是這次新增操作，不是保證任何 AI 未來都能零錯誤完成。問答語意、外部來源與最終呈現仍須檢查。後續發布網址設定會更新 project.json，與本次新增內容實驗分開。
