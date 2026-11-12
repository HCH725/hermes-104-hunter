---
name: hermes-104-hunter
description: Use when searching 104 jobs, calculating competitor counts via math, analyzing candidate tech stacks, or preparing safe HITL job applications.
---

# 🏹 Hermes 104 Job Hunter MCP Skill

當使用者要求在 **104 人力銀行** 進行求職職缺探索、企業待遇調研、競爭者情報精算或代填投遞視窗時，載入並使用此 Skill。

## 核心設計原則

1. **極致省靈力（Token 節流）**：
   - 搜尋結果預設僅列出核心摘要（標題、公司、地區、薪資、標籤）。
   - 嚴禁一次性向使用者倒進幾十個職缺，每次探測僅篩選並呈現 **3~5 個最契合的入圍職缺**。
   - 僅對入圍職缺呼叫詳情與競爭分析。
2. **純 API 優先**：
   - 95% 場景（搜尋、詳情、對手情報精算）走純 Python + HTTP API，不耗費記憶體啟動瀏覽器。
   - 對手真實應徵人數由數學逆推演算法精確求出（突破 30 人以上黑盒子）。
3. **Hit-in-the-Loop 安全邊界**：
   - 5% 場景（準備投遞）才按需喚醒 Playwright 實體視窗，將自薦信填妥並截圖。
   - **絕對不自動點擊最終送出按鈕**，將最後決定權留在人類手上。

---

## 可用 MCP 工具一覽

### 1. `job104_search`
搜尋 104 職缺。
* 參數：
  - `keyword` (str, 必填): 搜尋關鍵字（如 `"Python"`、`"後端架構師"`）。
  - `area` (str, 選填): 地區名稱（支援中文如 `"台北市"`、`"新竹市"`、`"台中市"`，會自動轉為 104 代碼）。
  - `page` (int, 預設 1): 頁碼。
  - `page_size` (int, 預設 20): 每頁筆數。
  - `order` (int, 預設 1): 排序方式（1: 相關性, 11: 更新日期）。
  - `exclude_negotiable` (bool, 預設 False): 是否過濾排除「面議」職缺。
  - `min_salary` (int, 選填): 最低月薪下限（如 `80000`）。
  - `remote_only` (bool, 預設 False): 是否僅搜尋「遠端工作」職缺。

### 2. `job104_job_detail`
取得指定職缺的完整結構化詳情。
* 參數：
  - `job_url_or_id` (str, 必填): 職缺網址或代碼（如 `"8nd15"` 或 `"https://www.104.com.tw/job/8nd15"`）。

### 3. `job104_apply_analysis`
【獨門絕技】獲取 104 內部統計資料與對手情報精算。
* 參數：
  - `job_url_or_id` (str, 必填): 職缺網址或代碼。
* 回傳重點：
  - `total_applicants`: 數學逆推精算出的確切應徵人數（若解唯一且充分；多解時為 None 並提供候選列表與概估說明）。
  - `total_basis`: 計算依據 (`inferred` 唯一精確解 / `ambiguous` 多解或資料不足 / `unknown` 無解)。
  - `education` / `age_distribution` / `experience_distribution`: 對手背景結構。
  - `top_skills`: 對手具備技能 Top 10（可用於自薦信突圍比對）。

### 4. `job104_get_my_templates`
讀取 104 帳號儲存的所有自我推薦信範本。
* 參數：
  - `job_url_or_id` (str, 必填): 任一有效的 104 職缺代碼。

### 5. `job104_prepare_application`
【Hit-in-the-Loop 代填投遞】開啟瀏覽器進入投遞彈窗，選取範本並塞入自薦信。
* 參數：
  - `job_url_or_id` (str, 必填): 目標職缺網址或代碼。
  - `template_title` (str, 選填): 欲選用的自薦信範本名稱。
  - `cover_letter_text` (str, 選填): AI 為候選人量身打造的自薦信內容。
  - `dry_run` (bool, 預設 False): 是否僅模擬測試與截圖。
