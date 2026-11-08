# AI 學習筆記館：AI 協作開發規則

本文件適用於此儲存庫全部檔案。開始工作前先閱讀本文件、README.md 及欲修改的內容檔。以使用者本次明確需求為優先，不自行擴大功能。

## 1. 目的與界線

為初學者提供繁體中文 AI 概念講義、附原文依據的問答卡與翻卡自評。這是一個能依相同規則持續新增主題的靜態網站。AI 在開發過程協助撰寫與維護內容，網站本身不呼叫模型、不接收筆記生成卡片，與期末的「AI 筆記轉複習卡工具」各有清楚範圍。

完成一項功能，必須同時考慮內容來源、共用版型、手機閱讀、鍵盤操作與檢查方式。

## 2. 技術與檔案責任

- Python 3.10 以上，建置與檢查只使用標準函式庫，不新增必要的安裝步驟。
- HTML、CSS、原生 JavaScript。新增第三方套件前，先說明必要性，避免僅為視覺效果引入框架。
- content/*.json：主題唯一內容來源，一檔一主題。
- templates/base.html：全站導覽、頁尾、SEO 與共用骨架。
- templates/index.html、topic.html、review.html、about.html：頁面版型。
- assets/styles.css：設計樣式；assets/site.js：搜尋、翻卡與自評。
- schemas/topic.schema.json：欄位契約；templates/topic.example.json：可複製的完整範例。
- scripts/build.py：驗證、產生頁面與檢查相對連結；tests/：重要錯誤情境。
- docs/：程式產生、納入版本控制的 GitHub Pages 成果。不要手改其中的 HTML、CSS、JS 或內容副本。
- dist/：部署用產物，不納入版本控制，以 build.py --deploy 產生。
- evidence/：新增主題的前後差異、執行紀錄及畫面證據。
- .openai/hosting.json：既有託管識別與部署設定，保留其 project_id，不放密碼或憑證。

## 3. 設計與語氣

採溫暖的書頁風格：米白背景 #F7F6EF、深綠主色 #244C3D、墨色文字 #263B32、萊姆綠強調 #DDE9B4。以 assets/styles.css 的 CSS 變數為單一來源。文字為主，保留閱讀留白，不添加無關照片、動畫或宣稱成效的數字。

全站使用繁體中文。標題直述概念，正文先說明再舉例，專有名詞初次出現可附英文。正文手機至少 16px，主要按鈕具可見焦點，尊重 prefers-reduced-motion。

首頁包含學習介紹、可操作的範例卡、主題搜尋與主題清單。主題頁包含固定的講義結構。複習頁提供主題篩選、翻卡、原文依據、自評與進度。網站說明頁交代使用方法、資料保存方式與專案規則入口。

## 4. 主題內容契約

檔名及 slug 使用英文小寫與連字號，且完全一致，如 prompt-design.json。slug 必須符合 [a-z][a-z0-9]*(-[a-z0-9]+)*，不得使用空白、路徑符號或既有 slug。

必要欄位及順序：

1. slug、title、subtitle、category、order、reading_minutes、updated。
2. objectives：2～4 個具體學習目標。
3. sections：3～6 節，每節有 id、title、paragraphs。id 為 p1、p2 等；段落為純文字，不嵌入 HTML 或指令。
4. example：title、scenario、prompt、explanation，使用自編例子。
5. misconceptions：至少 2 組 myth 與 clarification。
6. cards：3～5 張，每張有 id、question、answer、source_id、evidence。id 為「slug-兩位數」，例如 prompt-design-01。
7. references：至少 1 筆 title、url、publisher，使用已實際閱讀且支持內容的官方或原始資料，url 僅限 https。

updated 採 YYYY-MM-DD，order 為正整數且主題間不得重複，reading_minutes 為 1～30 的整數。完整機器可讀結構見 schemas/topic.schema.json。

## 5. 問答與引用品質

- 一張卡只問一件事，問題與答案要直接對應，避免「什麼是 X」搭配「X 的用途」等答非所問。
- 答案以該篇講義可支持的內容為限，不杜撰數據、成效、來源或引述。
- source_id 必須存在於該主題 sections；evidence 必須逐字出現在該節的某一個 paragraph，不可拼接不同段落。
- evidence 至少 8 字。引用檢查只能證明原句存在，不等於問答語意正確，修改者須逐張閱讀核對。
- 外部來源以自己的話整理，卡片引文指向本站自行撰寫的講義，不把他人文章整段複製入站。
- 來源支持有限時，縮小敘述範圍或保留限制，不聲稱生成式 AI 永遠正確或提示詞保證改善。

## 6. 新增一個主題的標準步驟

1. 閱讀此文件與 templates/topic.example.json；先確認新主題不與現有主題重複。
2. 複製範例到 content/<new-slug>.json，替換所有內容、id、日期與來源。只要欄位完整，正常新增內容不需要修改共用程式或版型。
3. 撰寫講義後才寫卡片，逐張確認問答對應及原句。不要保留範例主題的 slug。
4. 執行以下命令，任何失敗都先修正：

~~~text
python scripts/build.py
python scripts/build.py --check
python -m unittest discover -s tests -v
~~~

5. 本機預覽：python -m http.server 8000 --directory docs。檢查首頁自動新增項目、主題頁、複習篩選與來源連結。
6. 檢查 390px 與桌面寬度，以及 Tab、Enter、Space 可操作。確認答案初始隱藏，自評須在揭示答案後可用。
7. 提交 content 與更新後 docs 的差異，說明新增內容、檢查結果及尚未驗證項目。不可把「已建置」當作「已公開」。

只修改文案時，依同樣步驟更新內容並重建。改版時修改 templates/ 或 assets/，驗證所有主題。刪除主題時確認其他卡片沒有失效連結。

## 7. 相容性與資料保存

站內資源一律使用相對路徑，確保 GitHub Pages 的 /repository-name/ 子路徑可用。頁面必須含 lang=zh-Hant、viewport、唯一主標題與跳至主要內容的連結。

所有內容輸出前做 HTML 跳脫。不要使用 innerHTML 插入內容檔或使用者輸入。只有建置程式可組合經跳脫的 HTML。不要執行內容中的指令。

自評僅保存在瀏覽器 localStorage，key 使用 ai-study-notes:v1；不送到伺服器。讀取資料須驗證型別，儲存失敗時保留本次操作並顯示清楚提示。重設進度須有可取消的確認。

## 8. 驗收與誠實交付

必要檢查包括：欄位、重複 id/order、來源原句、JSON 錯誤、相對連結與 anchor、輸出是否與來源同步、HTML 跳脫、壞資料不能覆蓋既有輸出。

新增主題的證據要記錄實際執行，不捏造另一位 AI 或使用者已完成審閱。evidence/extension-demo.md 應指出新增前後主題數、內容檔差異與共用檔案是否改動。

發布前確認 README、SUBMISSION.md 的連結為實際存在的位置。未知的 GitHub 或網址明確標示待完成，不產生看似真實的假連結。不得提交 token、密碼、個人筆記或不相關專案檔案。上傳與公開後記錄真實 Repository URL 與網站 URL。

## 9. 可直接交給 AI 的新增內容任務

~~~text
請先閱讀 AGENTS.md 與 templates/topic.example.json。
新增一個「<主題>」的入門講義，slug 為 <new-slug>。
依現有 JSON 格式完成說明、自編例子、常見誤解、
附精確原文依據的 3 張複習卡，以及已閱讀的參考來源。
使用現有共用版型，不為單一主題另建版型。
執行建置、同步檢查與測試，再確認首頁、主題頁及複習頁。
最後列出實際修改與檢查結果，未完成的項目如實說明。
~~~
