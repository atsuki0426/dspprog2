# 個人課題2：気象庁 + 海外主要都市の天気アプリ
# Python 3.12 / flet / requests 前提

import requests
import flet as ft

# -----------------------------
# 日本向け：気象庁 API
# -----------------------------
AREA_LIST_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TEMPLATE_JMA = (
    "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
)

# -----------------------------
# 海外向け：Open-Meteo API
# -----------------------------
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# 海外の主要都市リスト（必要ならここに追加してOK）
OVERSEAS_CITIES = [
    {"name_ja": "ニューヨーク", "name_en": "New York", "lat": 40.7128, "lon": -74.0060},
    {"name_ja": "ロンドン", "name_en": "London", "lat": 51.5074, "lon": -0.1278},
    {"name_ja": "パリ", "name_en": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"name_ja": "シドニー", "name_en": "Sydney", "lat": -33.8688, "lon": 151.2093},
    {"name_ja": "ソウル", "name_en": "Seoul", "lat": 37.5665, "lon": 126.9780},
    {"name_ja": "ロサンゼルス", "name_en": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
    {"name_ja": "シンガポール", "name_en": "Singapore", "lat": 1.3521, "lon": 103.8198},
]


# ============================================================
# 共通：日本（気象庁）の地域リスト取得
# ============================================================
def load_area_groups():
    """
    area.json から「地方（centers）」ごとに「都道府県（offices）」を
    グルーピングして返す。

    戻り値:
        {
          "北海道地方": [{"code": "016000", "name": "北海道地方"}, ...],
          "東北地方":   [...],
          ...
        }
    のような辞書。
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

    # 表示を見やすくするためソート
    for center_name in groups:
        groups[center_name].sort(key=lambda a: a["name"])
    groups = dict(sorted(groups.items(), key=lambda kv: kv[0]))
    return groups


# ============================================================
# 日本：気象庁の天気予報取得
# ============================================================
def load_forecast_jma(area_code: str, max_days: int = 5):
    """
    指定した地域コードの天気予報を取得して、
    「日付」と「天気の文章」だけを抜き出して返す。

    戻り値:
        [
          {"date": "2025-12-21", "weather": "晴れ　時々　くもり"},
          ...
        ]
    """
    url = FORECAST_URL_TEMPLATE_JMA.format(area_code=area_code)
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()

    # data[0]["timeSeries"][0] に、天気の文章と日時が入っていることが多い
    time_series = data[0]["timeSeries"][0]
    time_defines = time_series["timeDefines"]  # 予報の対象時刻
    area0 = time_series["areas"][0]           # 最初のエリアだけ使う
    weathers = area0["weathers"]              # 天気の文章

    result = []
    for i, iso_dt in enumerate(time_defines[:max_days]):
        # "2025-12-21T00:00:00+09:00" → "2025-12-21"
        date = iso_dt.split("T")[0]
        weather = weathers[i] if i < len(weathers) else ""
        result.append({"date": date, "weather": weather})

    return result


# ============================================================
# 海外：Open-Meteo の weathercode → 日本語テキスト
# ============================================================
def weather_description_from_code(code: int) -> str:
    """
    Open-Meteo の WMO weathercode を簡単な日本語に変換。
    （Open-Meteo の WMOコード表をベースに作成）
    """
    if code == 0:
        return "晴れ"
    elif code in (1, 2, 3):
        return "晴れ〜くもり"
    elif code in (45, 48):
        return "霧・着氷霧"
    elif code in (51, 53, 55):
        return "霧雨（弱・中・強）"
    elif code in (56, 57):
        return "着氷性の霧雨（弱・強）"
    elif code in (61, 63, 65):
        return "雨（弱・中・強）"
    elif code in (66, 67):
        return "着氷性の雨（弱・強）"
    elif code in (71, 73, 75):
        return "雪（弱・中・強）"
    elif code == 77:
        return "雪あられ"
    elif code in (80, 81, 82):
        return "にわか雨（弱・中・強）"
    elif code in (85, 86):
        return "にわか雪（弱・強）"
    elif code == 95:
        return "雷雨"
    elif code in (96, 99):
        return "雷雨（ひょう）"
    else:
        return "不明"


# ============================================================
# 海外：Open-Meteo で予報取得
# ============================================================
def load_forecast_overseas(lat: float, lon: float, max_days: int = 5):
    """
    Open-Meteo API から海外都市の予報を取得して、
    日付 / 天気説明 / 最高・最低気温 をまとめて返す。
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min",
        "forecast_days": max_days,
        "timezone": "auto",  # 現地時間で日付を返してもらう
    }
    res = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()

    daily = data["daily"]
    times = daily["time"]
    codes = daily["weathercode"]
    tmax = daily["temperature_2m_max"]
    tmin = daily["temperature_2m_min"]

    result = []
    for i, date in enumerate(times[:max_days]):
        code = int(codes[i])
        desc = weather_description_from_code(code)
        result.append(
            {
                "date": date,
                "weather": f"{desc} / 最高 {tmax[i]:.1f}℃ 最低 {tmin[i]:.1f}℃",
            }
        )
    return result


# ============================================================
# Flet メイン
# ============================================================
def main(page: ft.Page):
    page.title = "天気予報アプリ（気象庁 + 海外）"

    # ウィンドウサイズを大きめに & 最小サイズも指定
    page.window_width = 1200
    page.window_height = 800
    page.window_min_width = 900
    page.window_min_height = 600
    page.window_resizable = True

    page.theme_mode = ft.ThemeMode.LIGHT

    # ステータス表示テキスト
    status_text = ft.Text("左のリストから地域・都市を選択してください。")

    # 右側：予報カードを並べるカラム
    forecast_column = ft.Column(spacing=10, scroll="auto")

    # --------------------------------------------------------
    # 共通：予報をカードで表示する関数
    # --------------------------------------------------------
    def show_forecasts(title: str, forecasts: list[dict]):
        status_text.value = title
        forecast_column.controls.clear()

        cards: list[ft.Control] = []
        for item in forecasts:
            card = ft.Card(
                content=ft.Container(
                    padding=10,
                    width=190,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                item["date"],
                                weight=ft.FontWeight.BOLD,
                                size=16,
                            ),
                            ft.Divider(),
                            ft.Text(item["weather"], size=14),
                        ],
                        tight=True,
                        spacing=5,
                    ),
                )
            )
            cards.append(card)

        # カードを横方向に並べる（折り返しあり）
        forecast_column.controls.append(
            ft.Row(controls=cards, wrap=True, spacing=10)
        )
        page.update()

    # --------------------------------------------------------
    # 日本（気象庁）が選ばれたとき
    # --------------------------------------------------------
    def on_select_area_jma(area_code: str, area_name: str):
        status_text.value = f"{area_name} ({area_code}) の天気予報を取得中..."
        forecast_column.controls.clear()
        page.update()

        try:
            forecasts = load_forecast_jma(area_code)
        except Exception as e:
            status_text.value = f"気象庁APIの取得でエラーが発生しました: {e}"
            page.update()
            return

        show_forecasts(f"{area_name} ({area_code}) の天気予報", forecasts)

    # --------------------------------------------------------
    # 海外（Open-Meteo）が選ばれたとき
    # --------------------------------------------------------
    def on_select_overseas(city: dict):
        name_ja = city["name_ja"]
        name_en = city["name_en"]
        lat = city["lat"]
        lon = city["lon"]

        status_text.value = f"{name_ja} / {name_en} の天気予報を取得中..."
        forecast_column.controls.clear()
        page.update()

        try:
            forecasts = load_forecast_overseas(lat, lon)
        except Exception as e:
            status_text.value = f"Open-Meteo API の取得でエラーが発生しました: {e}"
            page.update()
            return

        show_forecasts(f"{name_ja} / {name_en} の天気予報", forecasts)

    # --------------------------------------------------------
    # 左側：地域リスト（海外 + 日本）
    # --------------------------------------------------------
    try:
        area_groups = load_area_groups()
    except Exception as e:
        page.add(ft.Text(f"地域リストの取得に失敗しました（気象庁API）: {e}"))
        return

    expansion_tiles: list[ft.Control] = []

    # 1) 海外（Open-Meteo）のタイル
    overseas_tiles: list[ft.Control] = []
    for city in OVERSEAS_CITIES:
        def _on_click_overseas(e, city=city):
            on_select_overseas(city)

        overseas_tiles.append(
            ft.ListTile(
                title=ft.Text(f"{city['name_ja']} ({city['name_en']})"),
                subtitle=ft.Text(f"lat={city['lat']}, lon={city['lon']}"),
                on_click=_on_click_overseas,
                dense=True,
            )
        )

    overseas_expansion = ft.ExpansionTile(
        title=ft.Text("海外（Open-Meteo）"),
        controls=overseas_tiles,
        initially_expanded=False,
    )
    expansion_tiles.append(overseas_expansion)

    # 2) 日本（気象庁）のタイル
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
                ft.Text("地域・都市を選択", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Column(expansion_tiles, scroll="auto"),
            ],
            expand=True,
        ),
    )

    # 右側パネル（タイトル + ステータス + 予報カラム）
    right_panel = ft.Container(
        expand=True,
        padding=10,
        content=ft.Column(
            controls=[
                ft.Text("天気予報", size=22, weight=ft.FontWeight.BOLD),
                status_text,
                ft.Divider(),
                forecast_column,
            ],
            expand=True,
        ),
    )

    # レイアウト全体
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
    # ブラウザで起動するように設定
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)