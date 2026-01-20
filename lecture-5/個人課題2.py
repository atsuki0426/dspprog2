# main.py

import requests
import flet as ft

# -----------------------------
# 気象庁 API のエンドポイント
# -----------------------------
AREA_LIST_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TEMPLATE = (
    "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
)


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

    # parent（centers のコード）ごとに offices をまとめる
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


def load_forecast(area_code: str, max_days: int = 5):
    """
    指定した地域コードの天気予報を取得して、
    「日付」と「天気の文章」だけを抜き出して返す。

    戻り値のイメージ:
        [
          {"date": "2024-12-20", "weather": "晴れ　時々　くもり"},
          ...
        ]
    """
    url = FORECAST_URL_TEMPLATE.format(area_code=area_code)
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
        # "2024-12-20T00:00:00+09:00" → "2024-12-20"
        date = iso_dt.split("T")[0]
        weather = weathers[i] if i < len(weathers) else ""
        result.append({"date": date, "weather": weather})

    return result


def main(page: ft.Page):
    page.title = "天気予報アプリ（気象庁API）"

    # ウィンドウサイズを大きめに & 最小サイズも指定
    page.window_width = 1200
    page.window_height = 800
    page.window_min_width = 900
    page.window_min_height = 600
    page.window_resizable = True

    page.theme_mode = ft.ThemeMode.LIGHT

    # ステータス表示テキスト
    status_text = ft.Text("左のリストから地域を選択してください。")

    # 右側：予報カードを並べるカラム
    forecast_column = ft.Column(spacing=10, scroll="auto")

    # -----------------------------
    # 地域選択時の処理
    # -----------------------------
    def on_select_area(area_code: str, area_name: str):
        status_text.value = f"{area_name} ({area_code}) の天気予報を取得中..."
        forecast_column.controls.clear()
        page.update()

        try:
            forecasts = load_forecast(area_code)
        except Exception as e:
            status_text.value = f"エラーが発生しました: {e}"
            page.update()
            return

        status_text.value = f"{area_name} ({area_code}) の天気予報"

        # 取得した予報からカードを作る
        cards: list[ft.Control] = []
        for item in forecasts:
            card = ft.Card(
                content=ft.Container(
                    padding=10,
                    width=180,
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

    # -----------------------------
    # 左側：地域リスト（ExpansionTile + ListTile）
    # -----------------------------
    try:
        area_groups = load_area_groups()
    except Exception as e:
        # もし area.json の取得に失敗したらメッセージを出して終了
        page.add(ft.Text(f"地域リストの取得に失敗しました: {e}"))
        return

    expansion_tiles: list[ft.Control] = []

    for center_name, areas in area_groups.items():
        tiles: list[ft.Control] = []

        for area in areas:
            code = area["code"]
            name = area["name"]

            # ループ変数がクロージャでバグらないようにデフォルト引数に渡す
            def _on_click(e, code=code, name=name):
                on_select_area(code, name)

            tiles.append(
                ft.ListTile(
                    title=ft.Text(name),
                    subtitle=ft.Text(code),
                    on_click=_on_click,
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
        width=260,
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