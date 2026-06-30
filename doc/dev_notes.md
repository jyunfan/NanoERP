# 開發筆記

## 2026-06-30: UI-3 客戶訂單初始畫面

### 變更檔案
- `screens/order_screen.py`
- `nanoerp.tcss`

### 說明
- 客戶訂單初始狀態改為左側客戶清單、中央操作提示、右側產品總數。
- 移動客戶清單游標不再自動進入訂單明細；按 `Enter` 才載入所選客戶訂單。
- 初始狀態下 `Tab` 在客戶清單與產品總數間切換；進入客戶明細後 `Tab` 在客戶清單與訂單明細間切換。
- 產品總數讀取目前市場的 `order_draft` 加總，數量修改或刪除產品後會同步刷新。

## 2026-06-30: UI-3 客戶訂單 F3 售價模式

### 變更檔案
- `screens/order_screen.py`
- `doc/UI/UI-3-進銷訂貨處理.md`
- `SPEC.md`

### 說明
- 客戶訂單畫面新增 `F3` 售價模式切換；再按一次 `F3` 回到數量模式。
- 售價模式顯示 `名稱`、`進價`、`售價`；只有 `售價` 可編輯。
- `進價` 取自 `product.purchase_price`，只作參考，不在客戶訂單畫面修改。
- 客戶專用售價寫入 `customer_product.sale_price`；清空售價會刪除客戶專用價格，回到產品預設售價。

## 2026-06-30: UI-4 日報表子選單與出貨單畫面

### 變更檔案
- `menu_data.py`
- `screens/menu_screen.py`
- `screens/shipping_report_screen.py`
- `nanoerp.tcss`

### 說明
- `4.過帳與日報表 -> 2.日報表` 改為符合 UI-4 規格的子選單，包含 `1.出貨單` 與 `2.日帳單`。
- `1.出貨單` 進入出貨單預覽畫面；左側依市場列客戶與當日出貨筆數，右側顯示所選客戶的出貨單品項與數量。
- 出貨單資料來源為正式過帳後的 `order_table`，依 `app.work_date` 過濾，且暫不列入 `is_return` 退貨資料。
- `2.日帳單` 暫時沿用既有簡化版 `DailyReportScreen`。

## 2026-06-29: 訂單暫存與過帳資料流

### 變更檔案
- `create_db.py`
- `main.py`
- `screens/order_screen.py`
- `screens/posting_screen.py`
- `screens/menu_screen.py`
- `doc/DB.md`

### 設計計劃
- 使用者在客戶訂單畫面輸入的資料先寫入 `order_draft`，不直接寫入帶日期的正式訂單。
- `order_draft` 不存工作日期；工作日期只在執行過帳時使用。
- 過帳時建立 `posting_batch`，再把所有 `order_draft` 明細寫入 `order_table`，並用當下 `app.work_date` 作為 `order_date`。
- `order_table` 即為正式過帳明細，保存價格快照、過帳批次與過帳時間。
- 過帳完成後刪除已過帳的 `order_draft`，避免重複過帳。
- 日報表與結帳單只讀正式資料 `order_table`，所以過帳前暫存訂單不會出現在報表中。
- 現有 `order_table` 資料保留為正式歷史資料；migration 只補 schema，不把既有日期資料搬成無日期暫存資料。
- 補齊目前 `db.sql` 缺少但程式已使用的 `supplier_freq_product` 與 `purchase_order` 表。
- 開發階段直接移除重複的 `posting` 明細表與 `order_table.posted` 欄位；過帳狀態由 `posting_batch` 與 `order_table.order_date` 表達。

### DB 調整
- 新增 `order_draft`：客戶訂單暫存明細。
- 新增 `posting_batch`：一次過帳批次。
- 擴充 `order_table`：新增 `posting_batch_id`、`purchase_price`、`sale_price`、`posted_at`。
- 移除 `posting` table：不再複製一份與 `order_table` 重複的過帳明細。
- 移除 `order_table.posted`：正式訂單皆為過帳後資料，不需要額外旗標。
- App 啟動時會呼叫 DB 初始化，對既有 SQLite database 自動補齊缺少的表與欄位。

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
