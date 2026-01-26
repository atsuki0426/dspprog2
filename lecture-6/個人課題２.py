# 個人課題2 改良版：気象庁API + SQLite + 天気アイコン
# ファイル名例: kadai2_db_icon.py

import sqlite3
import requests
import flet as ft

# ==============================
# 設定
# ==============================

DB_PATH = "weather.db"

# 気象庁 API
AREA_LIST_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TEMPLATE_JMA = (
    "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
)

ICON_URL_TEMPLATE = "https://www.jma.go.jp/bosai/forecast/img/{code}.png"


# ==============================
# DB 関連
# ==============================

def init_db():
    """SQLite の初期化（テーブルがなければ作成）"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS forecasts (
                area_code     TEXT NOT NULL,
                area_name     TEXT NOT NULL,
                forecast_date TEXT NOT NULL,
                weather       TEXT NOT NULL,
                weather_code  TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (area_code, forecast_date)
            );
            """
        )
        conn.commit()


def save_forecasts_to_db(area_code: str, area_name: str, forecasts: list[dict]):
    """
    予報リストを DB に保存（INSERT OR REPLACE）。
    forecasts の要素:
        {"date": "YYYY-MM-DD", "weather": "天気の文章", "weather_code": "101"}
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        for item in forecasts:
            cur.execute(
                """
                INSERT OR REPLACE INTO forecasts
                    (area_code, area_name, forecast_date, weather, weather_code)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    area_code,
                    area_name,
                    item["date"],
                    item["weather"],
                    item["weather_code"],
                ),
            )
        conn.commit()


def load_forecasts_from_db(area_code: str, date: str | None = None) -> list[dict]:
    """
    DB から予報を読み出す。
    date を指定するとその日だけ、None のときは全部。
    戻り値: [{"date": "...", "weather": "...", "weather_code": "101"}, ...]
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        if date is None:
            cur.execute(
                """
                SELECT forecast_date, weather, weather_code
                FROM forecasts
                WHERE area_code = ?
                ORDER BY forecast_date;
                """,
                (area_code,),
            )
        else:
            cur.execute(
                """
                SELECT forecast_date, weather, weather_code
                FROM forecasts
                WHERE area_code = ? AND forecast_date = ?
                ORDER BY forecast_date;
                """,
                (area_code, date),
            )

        rows = cur.fetchall()

    return [
        {"date": r[0], "weather": r[1], "weather_code": r[2]}
        for r in rows
    ]


def load_dates_from_db(area_code: str) -> list[str]:
    """
    指定エリアの予報日付一覧（重複なし）を取得。
    ドロップダウンに使う。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT forecast_date
            FROM forecasts
            WHERE area_code = ?
            ORDER BY forecast_date;
            """,
            (area_code,),
        )
        rows = cur.fetchall()
    return [r[0] for r in rows]


# ==============================
# 気象庁 API 関連
# ==============================

def load_area_groups():
    """
    area.json から「地方（centers）」ごとに「都道府県（offices）」を
    グルーピングして返す。
    """
    res = requests.get(AREA_LIST_URL, timeout=10)
    res.raise_for_status()
    data = res.json()

    centers = data["centers"]  # 地方
    offices = data["offices"]  # 都道府県など

    groups: dict[str, list[dict]] = {}
    for code, info in offices.items():
        parent_code = info["parent"]
        center_name = centers.get(parent_code, {}).get("name", "その他")

        groups.setdefault(center_name, []).append(
            {"code": code, "name": info["name"]}
        )

    for center_name in groups:
        groups[center_name].sort(key=lambda a: a["name"])
    groups = dict(sorted(groups.items(), key=lambda kv: kv[0]))
    return groups


def load_forecast_jma(area_code: str, max_days: int = 5) -> list[dict]:
    """
    気象庁APIから天気予報を取得して、
    「日付」「天気の文章」「天気コード」を抜き出して返す。

    戻り値:
        [
          {"date": "2026-01-12", "weather": "晴れ　時々　くもり", "weather_code": "101"},
          ...
        ]
    """
    url = FORECAST_URL_TEMPLATE_JMA.format(area_code=area_code)
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()

    # data[0]["timeSeries"][0] に、天気の文章と weatherCodes が入っていることが多い
    time_series = data[0]["timeSeries"][0]
    time_defines = time_series["timeDefines"]
    area0 = time_series["areas"][0]
    weathers = area0["weathers"]
    weather_codes = area0.get("weatherCodes", [])

    result = []
    for i, iso_dt in enumerate(time_defines[:max_days]):
        date = iso_dt.split("T")[0]
        weather = weathers[i] if i < len(weathers) else ""
        code = weather_codes[i] if i < len(weather_codes) else ""
        result.append(
            {
                "date": date,
                "weather": weather,
                "weather_code": code,
            }
        )

    return result


# ==============================
# Flet メイン
# ==============================

def main(page: ft.Page):
    page.title = "天気予報アプリ（気象庁API + SQLite + アイコン）"

    # ウィンドウサイズ設定
    page.window_width = 1200
    page.window_height = 800
    page.window_min_width = 900
    page.window_min_height = 600
    page.window_resizable = True
    page.theme_mode = ft.ThemeMode.LIGHT

    # DB 初期化
    init_db()

    # 状態
    current_area = {"code": None, "name": None}

    # 画面パーツ
    status_text = ft.Text("左のリストから地域を選択してください。")
    forecast_column = ft.Column(spacing=10, scroll="auto")

    date_dropdown = ft.Dropdown(
        label="日付で絞り込み（任意）",
        options=[],
        on_change=lambda e: on_select_date(),
        width=250,
    )

    # -----------------------------
    # 共通：DBから読み出して表示
    # -----------------------------
    def show_forecasts_from_db(area_code: str, title_prefix: str, date: str | None = None):
        forecasts = load_forecasts_from_db(area_code, date=date)
        if date is None:
            status_text.value = f"{title_prefix} の天気予報（全日）"
        else:
            status_text.value = f"{title_prefix} の天気予報（{date}）"

        forecast_column.controls.clear()

        cards: list[ft.Control] = []
        for item in forecasts:
            icon_url = ""
            if item["weather_code"]:
                icon_url = ICON_URL_TEMPLATE.format(code=item["weather_code"])

            card_controls: list[ft.Control] = []

            # アイコンが取れそうなら画像を追加
            if icon_url:
                card_controls.append(
                    ft.Image(
                        src=icon_url,
                        width=64,
                        height=64,
                        fit=ft.ImageFit.CONTAIN,
                    )
                )

            # 日付＋天気テキスト
            card_controls.extend(
                [
                    ft.Text(
                        item["date"],
                        weight=ft.FontWeight.BOLD,
                        size=16,
                    ),
                    ft.Divider(),
                    ft.Text(item["weather"], size=14),
                ]
            )

            card = ft.Card(
                content=ft.Container(
                    padding=10,
                    width=200,
                    content=ft.Column(
                        controls=card_controls,
                        tight=True,
                        spacing=5,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
            cards.append(card)

        if not cards:
            forecast_column.controls.append(
                ft.Text("この条件に該当する予報はDBに保存されていません。")
            )
        else:
            forecast_column.controls.append(
                ft.Row(controls=cards, wrap=True, spacing=10)
            )

        page.update()

    # -----------------------------
    # 日付選択時
    # -----------------------------
    def on_select_date():
        if current_area["code"] is None:
            return
        selected_date = date_dropdown.value
        show_forecasts_from_db(
            current_area["code"],
            current_area["name"],
            date=selected_date if selected_date else None,
        )

    # -----------------------------
    # エリア選択時
    # -----------------------------
    def on_select_area_jma(area_code: str, area_name: str):
        current_area["code"] = area_code
        current_area["name"] = area_name

        status_text.value = f"{area_name} ({area_code}) の天気予報を取得中..."
        forecast_column.controls.clear()
        page.update()

        # 1. 気象庁APIから取得
        try:
            forecasts = load_forecast_jma(area_code)
        except Exception as e:
            status_text.value = f"気象庁APIの取得でエラーが発生しました: {e}"
            page.update()
            return

        # 2. DB に保存
        save_forecasts_to_db(area_code, area_name, forecasts)

        # 3. 日付ドロップダウン更新
        dates = load_dates_from_db(area_code)
        date_dropdown.options = [ft.dropdown.Option(d) for d in dates]
        date_dropdown.value = None
        date_dropdown.update()

        # 4. DB から読み出して表示
        show_forecasts_from_db(area_code, area_name, date=None)

    # -----------------------------
    # 左側：地域リスト
    # -----------------------------
    try:
        area_groups = load_area_groups()
    except Exception as e:
        page.add(ft.Text(f"地域リストの取得に失敗しました（気象庁API）: {e}"))
        return

    expansion_tiles: list[ft.Control] = []

    for center_name, areas in area_groups.items():
        tiles: list[ft.Control] = []

        for area in areas:
            code = area["code"]
            name = area["name"]

            def _on_click_jma(e, code=code, name=name):
                on_select_area_jma(code, name)

            tiles.append(
                ft.ListTile(
                    title=ft.Text(name),
                    subtitle=ft.Text(code),
                    on_click=_on_click_jma,
                    dense=True,
                )
            )

        expansion_tiles.append(
            ft.ExpansionTile(
                title=ft.Text(center_name),
                controls=tiles,
                initially_expanded=False,
            )
        )

    left_panel = ft.Container(
        width=280,
        bgcolor=ft.Colors.BLUE_GREY_50,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Text("地域を選択", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Column(expansion_tiles, scroll="auto"),
            ],
            expand=True,
        ),
    )

    right_panel = ft.Container(
        expand=True,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Text("天気予報（DB利用＋アイコン）", size=22, weight=ft.FontWeight.BOLD),
                status_text,
                date_dropdown,
                ft.Divider(),
                forecast_column,
            ],
            expand=True,
        ),
    )

    page.add(
        ft.Row(
            controls=[
                left_panel,
                right_panel,
            ],
            expand=True,
        )
    )


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)