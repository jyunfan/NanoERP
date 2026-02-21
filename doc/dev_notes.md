# 開發筆記

## 2026-02-22: 選單數字鍵快速選擇

### 變更檔案
- `screens/menu_screen.py`

### 說明
實作 UI.md 規格中「可以按數字鍵快速選擇選單項目」功能。

### 實作細節
- 在 `MenuScreen` 新增 `on_key` 方法，攔截數字鍵（0-9）按鍵事件
- 比對按下的數字與選單項目 label 前綴（如按 `1` 匹配 `"1. 客戶資料設定"`）
- 匹配成功後更新 `OptionList` 高亮狀態並直接導航
- 將導航邏輯抽取為 `_navigate_to` 方法，供 `on_option_list_option_selected` 和 `on_key` 共用
