# 🏹 Hermes 104 Job Hunter MCP

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Hermes 專屬 104 人力銀行求職特助 MCP**：集合「極輕量 API 探測」、「真實競爭人數數學逆推」與「Hit-in-the-Loop 代填投遞」優勢於一身的下一代求職自動化神兵。

---

## ▍為什麼打造這套工具？

現有的 104 MCP 專案往往面臨兩個極端：
1. **純後台治理型**：雖然輕量，但缺乏對手實戰競爭情報，且無法協助將信件帶入應徵視窗。
2. **全重裝瀏覽器型**：每次簡單查詢都要喚起幾百 MB 的 Chromium 實例，大量肥大 DOM 迅速灌爆 AI 的 Context Window (Token 暴走)。

**`hermes-104-hunter` 將兩者精華融合，並徹底踐行「極致效率」的架構心法：**

* ⚡ **95% 純 API 運作**：日常搜尋、條件過濾、職缺詳情與競爭情報**完全不開瀏覽器**，毫秒級回應，記憶體佔用小於 50MB。
* 🧮 **獨門數學逆推演算法**：突破 104 官方「30 人以上」的模糊黑盒子，以百分比最小公倍數與互斥維度約束，精確反推出**真實應徵人數**（如精準算出 42 人）與對手 Top 10 技能分佈。
* 🎭 **語氣克隆（拒絕 AI 罐頭感）**：主動調研你 104 帳號儲存的原版自薦信範本，讓 AI 撰寫客製信時完美繼承你的語氣長度與風格。
* 🛡️ **Hit-in-the-Loop (HITL) 安全鐵律**：僅在最後下達準備應徵時，才按需喚醒 Playwright 實體視窗代填自薦信並截圖；**絕不替人類自動點擊送出**，由使用者肉眼驗證後親手點下最後一步。

---

## ▍架構示意圖

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hermes 104 Job Hunter MCP                    │
├─────────────────────────────────────────────────────────────────┤
│ 【心法層 (Skill & SOP)】                                         │
│   • SKILL.md (Hermes 專屬技能規範)                              │
│   • AGENTS.md (五階段狀態機求職 SOP)                             │
│   • MY_PROFILE.md (求職者技能樹、薪資底線、黑名單紅線)          │
├─────────────────────────────────────────────────────────────────┤
│ 【輕量核心層 (95% 場景 - 純 Python + httpx)】                   │
│   • 認證：Chrome Cookie 無感提取 / 檔案掛載 / 匿名模式           │
│   • 搜尋：三級 Token 清洗 + 地區代碼自動轉換 + 排除面議/月薪篩選│
│   • 情報：純演算法逆推真實應徵人數與對手學經歷/Top 10 技能      │
├─────────────────────────────────────────────────────────────────┤
│ 【突擊代填層 (5% 場景 - 按需喚醒 Playwright)】                   │
│   • 代填投遞：自動開窗、切換指定範本、塞入客製推薦信並截圖      │
│   • HITL 安全邊界：保留實體視窗，絕不越權點擊送出               │
└─────────────────────────────────────────────────────────────────┘
```

---

## ▍五大核心工具

| 工具名稱 | 模式 | 核心亮點 |
| :--- | :---: | :--- |
| `job104_search` | 純 API | 支援中文地名解析（如「台北市」）、排除面議、薪資下限與完全遠端篩選。三級 Token 清洗，防止 Context 暴走。 |
| `job104_job_detail` | 純 API | 結構化提取職缺描述、技能需求、加分條件、學經歷門檻與 HR 聯絡人。 |
| `job104_apply_analysis` | **純 API + 數學** | **【獨門絕技】免啟動瀏覽器！** 逆推真實應徵人數，輸出對手學經歷與 Top 10 技能分佈，找出突圍盲點。 |
| `job104_get_my_templates` | 瀏覽器 | 讀取 104 帳號儲存的原版推薦信範本，供 AI 學習個人語氣。 |
| `job104_prepare_application` | 瀏覽器 (HITL) | 自動打開職缺視窗、切換範本、填入自薦信並截圖。**堅守安全邊界，絕不自動送出！** |

---

## ▍安裝與啟動

本專案使用現代 Python 套件管理器 [`uv`](https://github.com/astral-sh/uv) 構建。

### 1. 複製專案與安裝依賴

```bash
git clone https://github.com/HCH725/hermes-104-hunter.git
cd hermes-104-hunter

# 安裝 Python 依賴
uv sync

# 若需使用代填應徵功能，安裝 Playwright 瀏覽器核心
uv run playwright install chromium
```

### 2. 本地驗證測試

```bash
uv run pytest -v
```

---
## ▍接入設定 (Configuration)

### 接入 Hermes Agent

在 Hermes Agent 的 `config.yaml` 或 MCP 配置中加入：

```yaml
mcp_servers:
  hermes-104-hunter:
    command: "uv"
    args:
      - "run"
      - "--directory"
      - "/Users/hong/workspace/hermes-104-hunter"
      - "hermes-104-hunter"
    env:
      MCP_104_COOKIE_SOURCE: "chrome"  # 可選: chrome, file, env, none
```

### 接入 Claude Desktop

在 `claude_desktop_config.json` 中配置：

```json
{
  "mcpServers": {
    "hermes-104-hunter": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/hong/workspace/hermes-104-hunter",
        "hermes-104-hunter"
      ]
    }
  }
}
```

---

## ▍認證與 Cookie 設定

`hermes-104-hunter` 支援多種靈活認證方式：

1. **`chrome` 模式（預設）**：透過 `browser-cookie3` 自動讀取本機 Chrome 中 104 的登入 Session，免手動複製貼上。
2. **`file` 模式**：指定 `MCP_104_COOKIE_FILE=/path/to/cookies.json` 讀取匯出的 cookie。
3. **`env` 模式**：透過環境變數 `MCP_104_COOKIE="key=value; ..."` 直接注入。
4. **`none` 模式**：純公開匿名訪問。搜尋、職缺詳情與對手情報精算 **100% 正常運作**！

---

## ▍授權條款 (License)

本專案依據 [MIT 授權條款](LICENSE) 開源。
