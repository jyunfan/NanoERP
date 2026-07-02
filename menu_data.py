from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class MenuNode:
    id: str
    label: str
    children: list[MenuNode] = field(default_factory=list)
    is_back: bool = False
    title: str | None = None
    footer: str | None = None


MENU_TREE = MenuNode(
    id="root",
    label="NanoERP 主選單",
    children=[
        MenuNode(
            id="1",
            label="1. 客戶資料設定",
            children=[
                MenuNode(id="back", label="0. 回上一頁", is_back=True),
                MenuNode(id="1", label="1. 其餘市場"),
                MenuNode(id="2", label="2. 建國市場"),
                MenuNode(id="3", label="3. 南部市場"),
                MenuNode(id="supplier", label="4. 廠商"),
            ],
        ),
        MenuNode(id="2", label="2. 產品資料設定"),
        MenuNode(
            id="3",
            label="3. 進銷訂貨處理",
            children=[
                MenuNode(id="back", label="0. 回上一頁", is_back=True),
                MenuNode(
                    id="customer_orders",
                    label="1. 客戶訂單",
                    children=[
                        MenuNode(id="back", label="0. 回上一頁", is_back=True),
                        MenuNode(id="1", label="1. 其餘市場"),
                        MenuNode(id="2", label="2. 建國市場"),
                        MenuNode(id="3", label="3. 南部市場"),
                        MenuNode(id="total_check", label="4. 總數核對"),
                    ],
                ),
                MenuNode(id="purchase", label="2. 廠商訂單"),
            ],
        ),
        MenuNode(
            id="4",
            label="4.過帳與日報表",
            footer="0.回主系統  1.過帳  2.日報表",
            children=[
                MenuNode(id="back", label="0.回主系統", is_back=True),
                MenuNode(
                    id="posting",
                    label="1.過帳",
                    title="4.1 過帳與日報表\n過帳",
                    footer="0.回上系統  1.客戶退貨  2.執行過帳",
                    children=[
                        MenuNode(id="back", label="0.回上系統", is_back=True),
                        MenuNode(id="customer_return", label="1.客戶退貨"),
                        MenuNode(id="execute_posting", label="2.執行過帳"),
                    ],
                ),
                MenuNode(
                    id="daily_reports",
                    label="2.日報表",
                    title="4.2 過帳與日報表\n日報表",
                    footer="0.回上系統  1.出貨單  2.日帳單",
                    children=[
                        MenuNode(id="back", label="0.回上系統", is_back=True),
                        MenuNode(id="shipping", label="1.出貨單"),
                        MenuNode(
                            id="daily_account",
                            label="2.日帳單",
                            title="4.2.1 過帳與日報表\n日帳單",
                            footer="0.回上系統  1.列印者設定  2.執行",
                            children=[
                                MenuNode(id="back", label="0.回上系統", is_back=True),
                                MenuNode(id="print_settings", label="1.列印者設定"),
                                MenuNode(id="execute_daily_account", label="2.執行"),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        MenuNode(
            id="5",
            label="5.結帳與期報表",
            footer="0.回主系統  1.查帳  2.列印",
            children=[
                MenuNode(id="back", label="0.回主系統", is_back=True),
                MenuNode(
                    id="account_lookup",
                    label="1.查帳",
                    title="5.1 結帳與期報表\n查帳",
                    footer="0.回上系統  1.進銷明細  2.營業總額",
                    children=[
                        MenuNode(id="back", label="0.回上系統", is_back=True),
                        MenuNode(id="sales_detail", label="1.進銷明細"),
                        MenuNode(id="business_total", label="2.營業總額"),
                    ],
                ),
                MenuNode(id="period_print", label="2.列印"),
            ],
        ),
        MenuNode(id="6", label="6. 抄貨報表製作"),
        MenuNode(id="7", label="7. 系統維護檢查"),
    ],
)
