from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class MenuNode:
    id: str
    label: str
    children: list[MenuNode] = field(default_factory=list)
    is_back: bool = False


MENU_TREE = MenuNode(
    id="root",
    label="NanoERP 主選單",
    children=[
        MenuNode(
            id="1",
            label="1. 客戶資料設定",
            children=[
                MenuNode(id="back", label="1.0. 回上一頁", is_back=True),
                MenuNode(id="1", label="1. 其餘市場"),
                MenuNode(id="2", label="2. 建國市場"),
                MenuNode(id="3", label="3. 南部市場"),
            ],
        ),
        MenuNode(id="2", label="2. 產品資料設定"),
        MenuNode(id="3", label="3. 禁銷訂貨處理"),
        MenuNode(id="4", label="4. 過帳與日報表"),
        MenuNode(id="5", label="5. 結帳與其報表"),
        MenuNode(id="6", label="6. 抄貨報表製作"),
        MenuNode(id="7", label="7. 系統維護檢查"),
    ],
)
