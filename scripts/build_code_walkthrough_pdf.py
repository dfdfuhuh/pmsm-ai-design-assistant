"""Build a beginner-oriented Chinese PDF walkthrough from source snippets."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src" / "pmsm_ai"
OUTPUT_PDF = PROJECT_ROOT.parent / "PMSM-Python-Code-Walkthrough.pdf"
ASSET_ROOT = PROJECT_ROOT.parent / "PMSM-Python-Code-Walkthrough-assets"
CODE_IMAGE_DIR = ASSET_ROOT / "code"
PAGE_IMAGE_DIR = ASSET_ROOT / "pages"

FONT_CJK_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")
FONT_MONO_PATH = Path(r"C:\Windows\Fonts\consola.ttf")

PAGE_WIDTH = 11.69
PAGE_HEIGHT = 8.27
COLORS = {
    "dark": "#123f32",
    "green": "#207f5e",
    "light_green": "#edf7f2",
    "blue": "#285f7a",
    "light_blue": "#eef5f8",
    "amber": "#9a641c",
    "light_amber": "#fff5df",
    "text": "#20372f",
    "muted": "#62756d",
    "line": "#d6e3dc",
    "white": "#ffffff",
    "paper": "#f5f8f6",
}


@dataclass(frozen=True, slots=True)
class Snippet:
    """One code range and its teaching notes."""

    key: str
    title: str
    relative_file: str
    start_line: int
    end_line: int
    purpose: str
    flow: str
    points: tuple[str, ...]
    talk: str


SNIPPETS: tuple[Snippet, ...] = (
    Snippet(
        key="01_entry",
        title="程序从哪里开始",
        relative_file="src/pmsm_ai/__main__.py",
        start_line=1,
        end_line=5,
        purpose="入口文件只负责把启动工作交给 app.main。",
        flow="运行 python -m pmsm_ai 或打开 EXE → __main__.py → main() → app.py",
        points=(
            "import 从其他模块导入函数。",
            "if __name__ == '__main__' 只在直接运行时成立。",
            "SystemExit(main()) 把 main 的返回值作为退出码。",
        ),
        talk="这是程序总开关；真正创建窗口的代码在 app.py。",
    ),
    Snippet(
        key="02_app_main",
        title="创建窗口并进入事件循环",
        relative_file="src/pmsm_ai/app.py",
        start_line=324,
        end_line=341,
        purpose="创建 Qt 应用和主窗口，显示窗口，然后持续等待用户操作。",
        flow="create_application() → MainWindow() → show() → application.exec()",
        points=(
            "QApplication 管理 GUI 事件、字体和样式。",
            "exec() 不是算一次就结束，而是进入持续事件循环。",
            "--smoke-test 用 QTimer 自动退出，供便携包自检。",
        ),
        talk="GUI 是事件驱动：按钮点击后，事件循环才调用对应函数。",
    ),
    Snippet(
        key="03_current_design",
        title="把界面输入变成电机对象",
        relative_file="src/pmsm_ai/ui/dashboard.py",
        start_line=674,
        end_line=691,
        purpose="读取全部控件，组成字典，创建 PMSMDesign，并统一校验。",
        flow="点击预测 → current_design() → PMSMDesign(...) → validate()",
        points=(
            "inputs 字典把参数名与输入框对象对应起来。",
            "**values 把字典展开成对象关键字参数。",
            "界面只负责收集数据，不直接承担公式和 AI 计算。",
        ),
        talk="这里完成界面数据到业务对象的转换，是 GUI 与算法之间的桥。",
    ),
    Snippet(
        key="04_validate",
        title="电机参数为什么必须先校验",
        relative_file="src/pmsm_ai/domain.py",
        start_line=156,
        end_line=174,
        purpose="检查参数范围、定子内外径、转子机械空间和整数类型。",
        flow="PMSMDesign 对象 → validate() → 收集 errors → 有错则 raise ValueError",
        points=(
            "errors 列表可以一次报告多个问题，而不是遇到第一个就停。",
            "几何关系检查避免公式收到物理上不存在的设计。",
            "统一校验规则会被公式、AI、扫描和界面共同使用。",
        ),
        talk="这一步保证后面的模型不会拿明显不合理的电机参数做计算。",
    ),
    Snippet(
        key="05_service_predict",
        title="公式与 AI 的预测总调度",
        relative_file="src/pmsm_ai/service.py",
        start_line=75,
        end_line=92,
        purpose="一次预测同时调用解析公式和随机森林，并检查适用范围与电压。",
        flow=(
            "UI → PredictionService.predict() → analytical.evaluate() "
            "+ bundle.predict() → PredictionReport"
        ),
        points=(
            "PredictionReport 把多个结果装进一个对象统一返回。",
            "训练功率范围和电压可行性在这里判断。",
            "服务层组织流程，不负责画界面，也不重复写公式。",
        ),
        talk="这是项目的总调度员：界面、公式和 AI 在这里连接。",
    ),
    Snippet(
        key="06_analytical_main",
        title="把电机公式转换为 Python 计算",
        relative_file="src/pmsm_ai/analytical.py",
        start_line=47,
        end_line=66,
        purpose="计算气隙磁密、永磁磁链、转矩、频率、损耗、效率和电压。",
        flow="设计参数 → Bδ → ψf → 平均转矩 → 电频率/损耗/效率 → AnalyticalEvaluation",
        points=(
            "math.radians 把角度转换成弧度。",
            "中间量分开命名，便于核对单位和公式。",
            "返回 dataclass 对象，而不是难以维护的长元组。",
        ),
        talk="这段体现专业核心：结果由电机关系计算，不是直接猜一个数字。",
    ),
    Snippet(
        key="07_surrogate_predict",
        title="随机森林如何完成一次预测",
        relative_file="src/pmsm_ai/surrogate.py",
        start_line=75,
        end_line=92,
        purpose="按固定特征顺序构造二维数组，再调用三个目标模型。",
        flow="PMSMDesign → feature_dict() → 特征向量 → 三个模型 predict() → PerformancePrediction",
        points=(
            "feature_names 保证训练与推理的特征顺序一致。",
            "二维数组表示“1 个样本、多个特征”。",
            "三个输出分别由三个随机森林模型预测。",
        ),
        talk="AI 不是黑盒直接读界面，它接收的是标准化后的特征向量。",
    ),
    Snippet(
        key="08_scan",
        title="参数扫描为什么不乱连线",
        relative_file="src/pmsm_ai/service.py",
        start_line=94,
        end_line=111,
        purpose="固定其他参数，只改变一个参数，并保留不可行位置。",
        flow="linspace 生成采样点 → with_updates() → predict() → 公式值/AI值/有效性数组",
        points=(
            "不可行点记录 None，绘图时会形成断点。",
            "AI 点只在训练功率覆盖范围内保留。",
            "其他参数保持不变，才能称为单参数扫描。",
        ),
        talk="曲线漏洞的修复关键，就是不能偷偷删除不可行点。",
    ),
    Snippet(
        key="09_training_worker",
        title="后台训练为什么不会卡死界面",
        relative_file="src/pmsm_ai/ui/dashboard.py",
        start_line=132,
        end_line=151,
        purpose="把耗时训练放进 QObject Worker，通过信号报告状态。",
        flow="run() → train_and_save() → progress/finished/failed 信号 → 主界面更新",
        points=(
            "pyqtSignal 是后台线程与界面线程之间的事件通道。",
            "训练异常被捕获后通过 failed 信号返回。",
            "主线程继续处理窗口事件，所以界面不会冻结。",
        ),
        talk="耗时任务必须离开 GUI 主线程，这是本项目的重要工程处理。",
    ),
    Snippet(
        key="10_rf_train",
        title="随机森林是怎样训练和评估的",
        relative_file="src/pmsm_ai/surrogate.py",
        start_line=156,
        end_line=177,
        purpose="构造特征矩阵，分层划分数据，训练三个模型并计算指标。",
        flow="CSV → 派生特征 → 训练/验证/测试划分 → 三个 RandomForestRegressor → 指标与模型包",
        points=(
            "train_test_split 使用 stratify 保持各拓扑比例。",
            "每个目标分别 fit()，模型保存在 models 字典中。",
            "R2、MAE、RMSE 只评价对当前数据生成器的拟合。",
        ),
        talk="训练流程有固定随机种子和独立测试集，结果可复现。",
    ),
    Snippet(
        key="11_chart_plot",
        title="趋势图如何正确绘制",
        relative_file="src/pmsm_ai/ui/charts.py",
        start_line=121,
        end_line=138,
        purpose="把公式值和 AI 值转成数组，用 NaN 表示断点并绘制两张曲线。",
        flow="TrendSeries → numpy 数组 → 公式实线 + AI 虚线 → 坐标轴、图例和绘图区边距",
        points=(
            "None 转成 np.nan 后，Matplotlib 会自然断线。",
            "纵轴从 0 开始，避免近水平曲线被自动放大。",
            "横轴增加少量边距，防止首尾刻度被裁掉。",
        ),
        talk="图的逻辑与数据有效性绑定，不能把空缺区间连成直线。",
    ),
    Snippet(
        key="12_chart_nodes",
        title="主要节点为什么显示具体数字",
        relative_file="src/pmsm_ai/ui/charts.py",
        start_line=193,
        end_line=210,
        purpose="只给主要横轴刻度附近的 AI 点添加小字号数值。",
        flow="读取横轴刻度 → 找最近的有限 AI 点 → 判断端点 → annotate()",
        points=(
            "标注数量受限，避免全部 50 个点互相遮挡。",
            "首尾节点改变对齐方向，保证文字不出界。",
            "格式按输出目标区分：效率一位小数，转矩两位小数。",
        ),
        talk="这是图形可读性优化，不是改变模型数据。",
    ),
)


def _font(size: float, bold: bool = False) -> FontProperties:
    font = FontProperties(fname=str(FONT_CJK_PATH), size=size)
    if bold:
        font.set_weight("bold")
    return font


def _display_width(text: str) -> float:
    width = 0.0
    for character in text:
        width += 2.0 if unicodedata.east_asian_width(character) in "WF" else 1.0
    return width


def _wrap(text: str, max_units: float) -> list[str]:
    lines: list[str] = []
    current = ""
    current_units = 0.0
    for character in text:
        units = 2.0 if unicodedata.east_asian_width(character) in "WF" else 1.0
        if current and current_units + units > max_units:
            lines.append(current.rstrip())
            current = character.lstrip()
            current_units = _display_width(current)
        else:
            current += character
            current_units += units
    if current:
        lines.append(current.rstrip())
    return lines


def _token_color(style: object, token_type: object) -> str:
    spec = style.style_for_token(token_type)
    color = spec.get("color")
    return f"#{color}" if color else "#e5edf7"


def _code_lines(code: str) -> list[list[tuple[object, str]]]:
    lines: list[list[tuple[object, str]]] = [[]]
    for token_type, value in lex(code, PythonLexer()):
        parts = value.replace("\t", "    ").split("\n")
        for position, part in enumerate(parts):
            if part:
                lines[-1].append((token_type, part))
            if position < len(parts) - 1:
                lines.append([])
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _character_font(character: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_CJK_PATH if ord(character) > 127 else FONT_MONO_PATH
    return ImageFont.truetype(str(path), size)


def _render_code_image(snippet: Snippet) -> Path:
    source_path = PROJECT_ROOT / snippet.relative_file
    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    selected = "\n".join(source_lines[snippet.start_line - 1 : snippet.end_line])
    token_lines = _code_lines(selected)
    plain_lines = selected.splitlines()

    font_size = 18
    line_height = 28
    gutter_width = 78
    left_padding = 96
    right_padding = 28
    top_padding = 24
    bottom_padding = 24
    max_columns = max((_display_width(line) for line in plain_lines), default=20)
    image_width = max(
        1280,
        int(left_padding + max_columns * 10.2 + right_padding),
    )
    image_height = top_padding + bottom_padding + len(plain_lines) * line_height

    image = Image.new("RGB", (image_width, image_height), "#0f172a")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, gutter_width, image_height), fill="#111827")
    draw.line(
        (gutter_width, 0, gutter_width, image_height),
        fill="#314155",
        width=2,
    )

    line_number_font = ImageFont.truetype(str(FONT_MONO_PATH), font_size - 2)
    style = get_style_by_name("monokai")
    for line_index, tokens in enumerate(token_lines):
        source_number = snippet.start_line + line_index
        y = top_padding + line_index * line_height
        number = str(source_number)
        number_width = draw.textlength(number, font=line_number_font)
        draw.text(
            (gutter_width - 16 - number_width, y),
            number,
            font=line_number_font,
            fill="#718096",
        )
        x = float(left_padding)
        for token_type, value in tokens:
            color = _token_color(style, token_type)
            for character in value:
                character_font = _character_font(character, font_size)
                draw.text(
                    (x, y),
                    character,
                    font=character_font,
                    fill=color,
                )
                x += character_font.getlength(character)

    output_path = CODE_IMAGE_DIR / f"{snippet.key}.png"
    image.save(output_path)
    return output_path


def _rounded_box(
    figure: plt.Figure,
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
    edge: str,
) -> None:
    figure.patches.append(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            transform=figure.transFigure,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            facecolor=color,
            edgecolor=edge,
            linewidth=1.0,
        )
    )


def _page_header(
    figure: plt.Figure,
    title: str,
    kicker: str,
    page_number: int,
) -> None:
    figure.patches.append(
        Rectangle(
            (0, 0),
            1,
            1,
            transform=figure.transFigure,
            facecolor=COLORS["paper"],
            edgecolor="none",
            zorder=-100,
        )
    )
    figure.patches.append(
        Rectangle(
            (0, 0.91),
            1,
            0.09,
            transform=figure.transFigure,
            facecolor=COLORS["dark"],
            edgecolor="none",
            zorder=10,
        )
    )
    figure.text(
        0.055,
        0.954,
        kicker,
        color="#a6d8c5",
        fontproperties=_font(10, True),
        va="center",
        zorder=11,
    )
    figure.text(
        0.055,
        0.922,
        title,
        color="#ffffff",
        fontproperties=_font(18, True),
        va="center",
        zorder=11,
    )
    figure.text(
        0.955,
        0.035,
        f"PMSM AI Design Assistant  |  {page_number}",
        color=COLORS["muted"],
        fontproperties=_font(8),
        ha="right",
        zorder=11,
    )


def _fit_image_axes(
    figure: plt.Figure,
    image_path: Path,
    top: float,
    max_height: float,
) -> float:
    with Image.open(image_path) as image:
        image_width, image_height = image.size
    image_aspect = image_width / image_height
    max_width = 0.91
    axes_height = max_height
    axes_width = axes_height * (PAGE_HEIGHT / PAGE_WIDTH) * image_aspect
    if axes_width > max_width:
        axes_width = max_width
        axes_height = axes_width / image_aspect * (PAGE_WIDTH / PAGE_HEIGHT)
    left = (1.0 - axes_width) / 2.0
    bottom = top - max_height + (max_height - axes_height) / 2.0
    axes = figure.add_axes((left, bottom, axes_width, axes_height))
    axes.imshow(plt.imread(image_path), interpolation="nearest")
    axes.set_axis_off()
    return bottom


def _draw_lines(
    figure: plt.Figure,
    lines: list[str],
    x: float,
    y: float,
    size: float,
    color: str,
    step: float = 0.031,
) -> None:
    for line in lines:
        figure.text(
            x,
            y,
            line,
            color=color,
            fontproperties=_font(size),
            va="top",
        )
        y -= step


def _snippet_page(
    pdf: PdfPages,
    snippet: Snippet,
    code_image_path: Path,
    page_number: int,
) -> None:
    figure = plt.figure(figsize=(PAGE_WIDTH, PAGE_HEIGHT), facecolor=COLORS["paper"])
    _page_header(figure, snippet.title, "PYTHON 代码逐段讲解", page_number)
    figure.text(
        0.055,
        0.875,
        f"{snippet.relative_file}:{snippet.start_line}–{snippet.end_line}",
        color=COLORS["muted"],
        fontproperties=_font(9),
        va="top",
    )
    _fit_image_axes(figure, code_image_path, top=0.855, max_height=0.43)

    _rounded_box(figure, 0.055, 0.035, 0.555, 0.335, COLORS["white"], COLORS["line"])
    _rounded_box(figure, 0.63, 0.035, 0.315, 0.335, COLORS["light_amber"], "#ead8b4")

    figure.text(
        0.075,
        0.348,
        "这段代码的作用",
        color=COLORS["dark"],
        fontproperties=_font(12, True),
        va="top",
    )
    left_lines = ["- " + snippet.purpose, "", "执行过程："]
    left_lines.extend(_wrap(snippet.flow, 58))
    left_lines.extend(("", "需要看懂的 Python 点："))
    for point in snippet.points:
        wrapped = _wrap("- " + point, 66)
        left_lines.extend(wrapped)
    _draw_lines(figure, left_lines, 0.075, 0.318, 8.8, COLORS["text"], step=0.023)

    figure.text(
        0.65,
        0.348,
        "答辩时这样说",
        color=COLORS["amber"],
        fontproperties=_font(12, True),
        va="top",
    )
    _draw_lines(
        figure,
        _wrap("“" + snippet.talk + "”", 34),
        0.65,
        0.318,
        9.4,
        COLORS["text"],
        step=0.029,
    )
    figure.text(
        0.65,
        0.19,
        "输入 → 处理 → 输出",
        color=COLORS["amber"],
        fontproperties=_font(10.5, True),
        va="top",
    )
    _draw_lines(
        figure,
        _wrap(snippet.flow, 38),
        0.65,
        0.165,
        8.2,
        COLORS["muted"],
        step=0.023,
    )

    page_path = PAGE_IMAGE_DIR / f"page-{page_number:02d}-{snippet.key}.png"
    figure.savefig(page_path, dpi=120, facecolor=figure.get_facecolor())
    pdf.savefig(figure)
    plt.close(figure)


def _flow_box(
    figure: plt.Figure,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    subtitle: str,
    color: str,
) -> None:
    _rounded_box(figure, x, y, width, height, color, COLORS["line"])
    figure.text(
        x + width / 2,
        y + height * 0.62,
        title,
        color=COLORS["text"],
        fontproperties=_font(10.5, True),
        ha="center",
        va="center",
    )
    figure.text(
        x + width / 2,
        y + height * 0.29,
        subtitle,
        color=COLORS["muted"],
        fontproperties=_font(8.2),
        ha="center",
        va="center",
    )


def _arrow(figure: plt.Figure, start: tuple[float, float], end: tuple[float, float]) -> None:
    figure.patches.append(
        FancyArrowPatch(
            start,
            end,
            transform=figure.transFigure,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.2,
            color=COLORS["green"],
        )
    )


def _cover_page(pdf: PdfPages) -> int:
    figure = plt.figure(figsize=(PAGE_WIDTH, PAGE_HEIGHT), facecolor=COLORS["dark"])
    figure.patches.append(
        Rectangle(
            (0, 0),
            1,
            1,
            transform=figure.transFigure,
            facecolor=COLORS["dark"],
            edgecolor="none",
        )
    )
    figure.patches.append(
        Rectangle(
            (0.065, 0.105),
            0.012,
            0.68,
            transform=figure.transFigure,
            facecolor="#53b58d",
            edgecolor="none",
        )
    )
    figure.text(
        0.105,
        0.72,
        "PMSM AI DESIGN ASSISTANT",
        color="#a6d8c5",
        fontproperties=_font(12, True),
        va="top",
    )
    figure.text(
        0.105,
        0.625,
        "Python 代码答辩讲解手册",
        color="#ffffff",
        fontproperties=_font(31, True),
        va="top",
    )
    figure.text(
        0.105,
        0.525,
        "从程序入口到公式、AI 和趋势图的完整执行链",
        color="#dceee7",
        fontproperties=_font(16),
        va="top",
    )
    figure.text(
        0.105,
        0.25,
        "适合：Python 初学者、课程项目答辩、源码自学",
        color="#b8d8cb",
        fontproperties=_font(12),
        va="top",
    )
    figure.text(
        0.105,
        0.19,
        "记录日期：2026-11-20",
        color="#b8d8cb",
        fontproperties=_font(11),
        va="top",
    )
    figure.text(
        0.105,
        0.13,
        "代码版本：main / 41 项自动化测试通过",
        color="#8fc6af",
        fontproperties=_font(10),
        va="top",
    )
    pdf.savefig(figure)
    figure.savefig(
        PAGE_IMAGE_DIR / "page-01-cover.png",
        dpi=120,
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return 2


def _architecture_page(pdf: PdfPages, page_number: int) -> int:
    figure = plt.figure(figsize=(PAGE_WIDTH, PAGE_HEIGHT), facecolor=COLORS["paper"])
    _page_header(
        figure,
        "项目全景：一次预测是怎样跑起来的",
        "先看整体，不急着读细节",
        page_number,
    )
    _flow_box(figure, 0.06, 0.63, 0.17, 0.14, "__main__.py", "入口", COLORS["white"])
    _flow_box(figure, 0.27, 0.63, 0.17, 0.14, "app.py", "创建窗口 / 事件循环", COLORS["white"])
    _flow_box(
        figure,
        0.48,
        0.63,
        0.2,
        0.14,
        "ui/dashboard.py",
        "读取参数 / 点击事件",
        COLORS["white"],
    )
    _flow_box(
        figure,
        0.72,
        0.63,
        0.21,
        0.14,
        "service.py",
        "组织预测流程",
        COLORS["light_green"],
    )
    _flow_box(
        figure,
        0.72,
        0.42,
        0.21,
        0.13,
        "analytical.py",
        "公式基准",
        COLORS["light_blue"],
    )
    _flow_box(
        figure,
        0.72,
        0.22,
        0.21,
        0.13,
        "surrogate.py",
        "随机森林 AI",
        COLORS["light_amber"],
    )
    _flow_box(
        figure,
        0.44,
        0.42,
        0.2,
        0.13,
        "domain.py",
        "参数对象 / 校验",
        COLORS["white"],
    )
    _flow_box(
        figure,
        0.44,
        0.22,
        0.2,
        0.13,
        "ui/charts.py",
        "公式 / AI 趋势图",
        COLORS["white"],
    )
    _arrow(figure, (0.23, 0.7), (0.27, 0.7))
    _arrow(figure, (0.44, 0.7), (0.48, 0.7))
    _arrow(figure, (0.68, 0.7), (0.72, 0.7))
    _arrow(figure, (0.825, 0.63), (0.825, 0.55))
    _arrow(figure, (0.825, 0.42), (0.825, 0.35))
    _arrow(figure, (0.64, 0.485), (0.72, 0.485))
    _arrow(figure, (0.64, 0.285), (0.72, 0.285))

    figure.text(
        0.06,
        0.54,
        "最值得背下来的主链",
        color=COLORS["dark"],
        fontproperties=_font(14, True),
        va="top",
    )
    chain_lines = [
        "按钮点击",
        "→ current_design() 读取 16 个参数",
        "→ PMSMDesign.validate() 检查合理性",
        "→ PredictionService.predict() 总调度",
        "→ 解析公式与随机森林分别给出结果",
        "→ 卡片显示数值，趋势图显示单参数变化",
    ]
    _draw_lines(figure, chain_lines, 0.06, 0.49, 11.2, COLORS["text"], step=0.041)

    figure.text(
        0.06,
        0.16,
        "答辩先讲这张图，再按箭头进入代码，比逐个文件念更容易听懂。",
        color=COLORS["green"],
        fontproperties=_font(11, True),
        va="top",
    )
    pdf.savefig(figure)
    figure.savefig(
        PAGE_IMAGE_DIR / "page-02-architecture.png",
        dpi=120,
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return page_number + 1


def _ending_page(pdf: PdfPages, page_number: int) -> int:
    figure = plt.figure(figsize=(PAGE_WIDTH, PAGE_HEIGHT), facecolor=COLORS["paper"])
    _page_header(figure, "答辩顺序与常见问题", "最后一页：照着讲即可", page_number)

    _rounded_box(figure, 0.055, 0.48, 0.56, 0.36, COLORS["white"], COLORS["line"])
    _rounded_box(figure, 0.64, 0.48, 0.305, 0.36, COLORS["light_blue"], "#cbdde7")
    _rounded_box(figure, 0.055, 0.08, 0.89, 0.35, COLORS["light_amber"], "#ead8b4")

    figure.text(
        0.075,
        0.80,
        "建议的 8 分钟顺序",
        color=COLORS["dark"],
        fontproperties=_font(13, True),
        va="top",
    )
    agenda = [
        "1. 30 秒：项目目标与五种拓扑",
        "2. 1 分钟：入口与 GUI 事件循环",
        "3. 1 分钟：界面参数 → PMSMDesign",
        "4. 1.5 分钟：参数校验与对象设计",
        "5. 2 分钟：电机公式与解析基准",
        "6. 1.5 分钟：随机森林训练与预测",
        "7. 1 分钟：扫描断点和图表对照",
        "8. 30 秒：数据边界与后续 FEA",
    ]
    _draw_lines(figure, agenda, 0.075, 0.75, 9.6, COLORS["text"], step=0.034)

    figure.text(
        0.66,
        0.80,
        "老师可能追问",
        color=COLORS["blue"],
        fontproperties=_font(13, True),
        va="top",
    )
    questions = [
        "Q：为什么同时有公式和 AI？",
        "A：公式提供可解释基准，AI 提供快速代理结果。",
        "",
        "Q：数据是真实 FEA 吗？",
        "A：当前是合成解析基线，尚未完成 FEA 校准。",
        "",
        "Q：如何防止乱输入？",
        "A：domain.validate + 训练功率边界 + 电压检查。",
    ]
    _draw_lines(figure, questions, 0.66, 0.75, 9.1, COLORS["text"], step=0.034)

    figure.text(
        0.075,
        0.405,
        "必须主动说明的三个边界",
        color=COLORS["amber"],
        fontproperties=_font(13, True),
        va="top",
    )
    boundaries = [
        "1. R2 只说明拟合合成数据生成器，不代表真实电机精度。",
        "2. 趋势图是固定其他参数后的单参数扫描，不是完整优化结果。",
        "3. 便携版目标是快速方案筛选，正式设计仍需 Maxwell/JMAG 或实测。",
        "4. 相电阻和相电感是独立高级输入，不随匝数自动重算。",
    ]
    y = 0.355
    for boundary in boundaries:
        lines = _wrap(boundary, 95)
        _draw_lines(figure, lines, 0.075, y, 10.5, COLORS["text"], step=0.035)
        y -= 0.035 * len(lines) + 0.018

    pdf.savefig(figure)
    figure.savefig(
        PAGE_IMAGE_DIR / "page-final-summary.png",
        dpi=120,
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return page_number + 1


def main() -> int:
    if not FONT_CJK_PATH.is_file() or not FONT_MONO_PATH.is_file():
        raise FileNotFoundError("缺少微软/黑体或 Consolas 字体，无法生成代码截图")
    CODE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    PAGE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    code_images = {
        snippet.key: _render_code_image(snippet)
        for snippet in SNIPPETS
    }
    with PdfPages(OUTPUT_PDF) as pdf:
        page_number = _cover_page(pdf)
        page_number = _architecture_page(pdf, page_number)
        for snippet in SNIPPETS:
            _snippet_page(pdf, snippet, code_images[snippet.key], page_number)
            page_number += 1
        _ending_page(pdf, page_number)

    print(f"PDF: {OUTPUT_PDF}")
    print(f"代码截图: {CODE_IMAGE_DIR}")
    print(f"页面预览: {PAGE_IMAGE_DIR}")
    print(f"页数: {page_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
