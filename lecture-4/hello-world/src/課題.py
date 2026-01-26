import math
import random   # Rand ボタン用

import flet as ft


class CalcButton(ft.ElevatedButton):
    def __init__(self, text, button_clicked, expand=1):
        super().__init__()
        self.text = text
        self.expand = expand
        self.on_click = button_clicked
        self.data = text


class DigitButton(CalcButton):
    def __init__(self, text, button_clicked, expand=1):
        super().__init__(text, button_clicked, expand)
        self.bgcolor = ft.Colors.WHITE24
        self.color = ft.Colors.WHITE


class OpButton(CalcButton):
    def __init__(self, text, button_clicked, expand=1):
        super().__init__(text, button_clicked, expand)
        self.bgcolor = ft.Colors.ORANGE
        self.color = ft.Colors.WHITE


class FuncButton(CalcButton):
    def __init__(self, text, button_clicked, expand=1):
        super().__init__(text, button_clicked, expand)
        self.bgcolor = ft.Colors.BLUE_GREY_100
        self.color = ft.Colors.BLACK


class CalculatorApp(ft.Container):
    def __init__(self):
        super().__init__()
        self.reset()

        self.memory = 0.0          # mc, m+, m-, mr 用
        self.use_radians = True    # Rad / Deg 切り替え

        # 上段: 式表示 / 下段: 結果表示
        self.expression_text = ft.Text(value="", color=ft.Colors.WHITE70, size=18)
        self.result = ft.Text(value="0", color=ft.Colors.WHITE, size=32)

        self.width = 600
        self.bgcolor = ft.Colors.BLACK
        self.border_radius = ft.border_radius.all(20)
        self.padding = 20

        # 🔽 ボタン配置：Mac の関数電卓にかなり寄せた形
        layout = [
            ["(", ")", "mc", "m+", "m-", "mr", "AC", "+/-", "%", "÷"],
            ["2nd", "x²", "x³", "xʸ", "eˣ", "10ˣ", "7", "8", "9", "×"],
            ["1/x", "²√x", "³√x", "ʸ√x", "ln", "log₁₀", "4", "5", "6", "−"],
            ["x!", "sin", "cos", "tan", "e", "EE", "1", "2", "3", "+"],
            ["", "sinh", "cosh", "tanh", "π", "Rad", "Rand", "0", ".", "="],
        ]

        rows = []
        for row_labels in layout:
            buttons = []
            for label in row_labels:
                if label in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."):
                    btn = DigitButton(label, self.button_clicked)
                elif label in ("÷", "×", "−", "/", "*", "-", "+", "="):
                    btn = OpButton(label, self.button_clicked)
                else:
                    btn = FuncButton(label, self.button_clicked)

                if label == "0":
                    btn.expand = 2  # 0 だけ横長に

                buttons.append(btn)
            rows.append(
                ft.Row(controls=buttons, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

        self.content = ft.Column(
            controls=[
                ft.Row(controls=[self.expression_text], alignment=ft.MainAxisAlignment.END),
                ft.Row(controls=[self.result], alignment=ft.MainAxisAlignment.END),
                *rows,
            ]
        )

    # =============================================================

    def button_clicked(self, e: ft.ControlEvent):
        data = e.control.data
        print(f"Button clicked: {data}")

        # Error 表示中は AC 以外無視
        if self.result.value == "Error" and data != "AC":
            return

        # --- AC ---
        if data == "AC":
            self.result.value = "0"
            self.expression_text.value = ""
            self.reset()
            self.update()
            return

        # --- 数字・小数点 ---
        if data in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."):
            if self.result.value == "0" or self.new_operand:
                # 新しい数の入力開始
                self.result.value = data if data != "." else "0."
                self.new_operand = False
            else:
                # 後ろに足していく
                if data == "." and "." in str(self.result.value):
                    pass  # 小数点2個目は無視
                else:
                    self.result.value = str(self.result.value) + data

            self.update()
            return

        # --- 符号反転 ---
        if data == "+/-":
            try:
                v = float(str(self.result.value))
                v = -v
                self.result.value = str(self.format_number(v))
            except Exception:
                self.result.value = "Error"
                self.reset()
            self.update()
            return

        # --- パーセント ---
        if data == "%":
            try:
                v = float(str(self.result.value))
                v = v / 100.0
                self.result.value = str(self.format_number(v))
                self.new_operand = True
            except Exception:
                self.result.value = "Error"
                self.reset()
            self.update()
            return

        # --- メモリ系 ---
        if data == "mc":
            self.memory = 0.0
            self.update()
            return
        if data == "m+":
            try:
                self.memory += float(str(self.result.value))
                self.new_operand = True
            except Exception:
                self.result.value = "Error"
                self.reset()
            self.update()
            return
        if data == "m-":
            try:
                self.memory -= float(str(self.result.value))
                self.new_operand = True
            except Exception:
                self.result.value = "Error"
                self.reset()
            self.update()
            return
        if data == "mr":
            self.result.value = str(self.format_number(self.memory))
            self.new_operand = True
            self.update()
            return

        # --- Rad / Deg 切り替え ---
        if data == "Rad" or data == "Deg":
            self.use_radians = not self.use_radians
            e.control.text = "Rad" if self.use_radians else "Deg"
            e.control.update()
            return

        # --- Rand（0〜1の乱数） ---
        if data == "Rand":
            self.result.value = str(self.format_number(random.random()))
            self.new_operand = True
            self.update()
            return

        # --- 定数 ---
        if data == "π":
            self.result.value = str(self.format_number(math.pi))
            self.new_operand = True
            self.update()
            return
        if data == "e":
            self.result.value = str(self.format_number(math.e))
            self.new_operand = True
            self.update()
            return

        # ここから先は「今表示されている値に対する単項演算」
        try:
            v = float(str(self.result.value))
        except Exception:
            v = None

        if v is not None:
            if data == "x²":
                v = v ** 2
            elif data == "x³":
                v = v ** 3
            elif data == "eˣ":
                v = math.exp(v)          # e^x
            elif data == "10ˣ":
                v = 10 ** v              # 10^x
            elif data == "1/x":
                if v == 0:
                    self.result.value = "Error"
                    self.reset()
                    self.update()
                    return
                v = 1.0 / v
            elif data == "²√x":
                if v < 0:
                    self.result.value = "Error"
                    self.reset()
                    self.update()
                    return
                v = math.sqrt(v)
            elif data == "³√x":
                # 負にも対応した 3 乗根
                v = math.copysign(abs(v) ** (1.0 / 3.0), v)
            elif data == "x!":
                if v < 0 or int(v) != v:
                    self.result.value = "Error"
                    self.reset()
                    self.update()
                    return
                v = math.factorial(int(v))
            elif data == "sin":
                angle = v if self.use_radians else math.radians(v)
                v = math.sin(angle)
            elif data == "cos":
                angle = v if self.use_radians else math.radians(v)
                v = math.cos(angle)
            elif data == "tan":
                angle = v if self.use_radians else math.radians(v)
                v = math.tan(angle)
            elif data == "sinh":
                v = math.sinh(v)
            elif data == "cosh":
                v = math.cosh(v)
            elif data == "tanh":
                v = math.tanh(v)
            elif data == "ln":
                if v <= 0:
                    self.result.value = "Error"
                    self.reset()
                    self.update()
                    return
                v = math.log(v)
            elif data == "log₁₀":      # ← レイアウトと合わせた
                if v <= 0:
                    self.result.value = "Error"
                    self.reset()
                    self.update()
                    return
                v = math.log10(v)
            else:
                v = None  # 未対応ボタン

            if v is not None:
                self.result.value = str(self.format_number(v))
                self.new_operand = True
                self.update()
                return

        # --- xʸ（べき乗演算の開始） ---
        if data in ("xʸ", "yˣ"):
            try:
                self.operand1 = float(str(self.result.value))
                self.operator = "pow"
                self.new_operand = True
                self.expression_text.value = f"{self.result.value} ^"
                self.update()
                return
            except Exception:
                self.result.value = "Error"
                self.reset()
                self.update()
                return

        # --- ʸ√x（y乗根：x^(1/y) の y 部分をセット） ---
        if data == "ʸ√x":
            try:
                # 今の表示 = y（根の次数）
                self.operand1 = float(str(self.result.value))  # y
                self.operator = "yroot"
                self.new_operand = True
                self.expression_text.value = f"{self.result.value} √"
                self.update()
                return
            except Exception:
                self.result.value = "Error"
                self.reset()
                self.update()
                return

        # --- 四則演算 & "=" ---
        if data in ("+", "-", "*", "/", "÷", "×", "−", "="):
            # 表示用と内部用の記号を分ける
            op_symbol = data
            if data == "÷":
                op = "/"
            elif data == "×":
                op = "*"
            elif data == "−":
                op = "-"
            else:
                op = data

            try:
                current = float(str(self.result.value))
            except Exception:
                self.result.value = "Error"
                self.reset()
                self.update()
                return

            # 直前の演算を反映
            self.result.value = str(self.calculate(self.operand1, current, self.operator))
            if self.result.value == "Error":
                self.operand1 = 0
                self.operator = "+"
                self.new_operand = True
                self.expression_text.value = ""
                self.update()
                return

            # 式表示を更新
            if data != "=":
                self.expression_text.value = f"{self.result.value} {op_symbol}"
                self.operand1 = float(self.result.value)
                self.operator = op
                self.new_operand = True
            else:
                self.expression_text.value = ""
                self.reset()

            self.update()
            return

        # それ以外（2nd, EE, (), 空ボタンなど）は今は未実装
        print(f"'{data}' button is not implemented yet.")

    # =============================================================

    def format_number(self, num):
        if isinstance(num, (int, float)) and num % 1 == 0:
            return int(num)
        else:
            return num

    def calculate(self, operand1, operand2, operator):
        try:
            if operator == "+":
                return self.format_number(operand1 + operand2)
            elif operator == "-":
                return self.format_number(operand1 - operand2)
            elif operator == "*":
                return self.format_number(operand1 * operand2)
            elif operator == "/":
                if operand2 == 0:
                    return "Error"
                return self.format_number(operand1 / operand2)
            elif operator == "pow":
                return self.format_number(operand1 ** operand2)
            elif operator == "yroot":
                # y√x = x^(1/y)
                y = operand1
                x = operand2
                if y == 0:
                    return "Error"
                # 偶数根で負数はNG
                if x < 0 and int(y) % 2 == 0:
                    return "Error"
                return self.format_number(x ** (1.0 / y))
            else:
                # 初回は「0 + 現在値」とみなす
                return self.format_number(operand2)
        except Exception:
            return "Error"

    def reset(self):
        self.operator = "+"
        self.operand1 = 0.0
        self.new_operand = True


def main(page: ft.Page):
    page.title = "Scientific Calculator (simple)"
    calc = CalculatorApp()
    page.add(calc)


ft.app(main)