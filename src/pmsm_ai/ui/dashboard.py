"""Interactive PMSM design workbench."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pmsm_ai.domain import (
    DEFAULT_DESIGN,
    PARAMETER_SPECS,
    SPM_TOPOLOGIES,
    PMSMDesign,
)
from pmsm_ai.environment import EnvironmentCheck, all_checks_passed, collect_environment_checks
from pmsm_ai.paths import (
    DEFAULT_DATASET_PATH,
    DEFAULT_METRICS_PATH,
    DEFAULT_MODEL_PATH,
)
from pmsm_ai.service import PredictionReport, PredictionService
from pmsm_ai.surrogate import TARGET_LABELS, ModelBundle
from pmsm_ai.training import train_and_save
from pmsm_ai.ui.charts import ImportancePlotCanvas, TrendPlotCanvas
from pmsm_ai.ui.widgets import MetricCard

BASIC_PARAMETER_NAMES = (
    "stator_outer_diameter_mm",
    "stator_inner_diameter_mm",
    "stack_length_mm",
    "air_gap_mm",
    "magnet_thickness_mm",
    "turns_per_phase",
    "rated_current_a",
    "speed_rpm",
)
ADVANCED_ELECTRICAL_NAMES = (
    "current_angle_deg",
    "magnet_remanence_t",
    "phase_resistance_ohm",
    "phase_inductance_mh",
    "dc_bus_voltage_v",
)
ADVANCED_MECHANICAL_NAMES = (
    "slot_opening_mm",
    "rotor_yoke_thickness_mm",
    "shaft_diameter_mm",
)


class TrainingWorker(QObject):
    """Run model training outside the GUI thread."""

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        dataset_path: Path = DEFAULT_DATASET_PATH,
        model_path: Path = DEFAULT_MODEL_PATH,
        metrics_path: Path = DEFAULT_METRICS_PATH,
    ) -> None:
        super().__init__()
        self.dataset_path = dataset_path
        self.model_path = model_path
        self.metrics_path = metrics_path

    @pyqtSlot()
    def run(self) -> None:
        try:
            bundle = train_and_save(
                dataset_path=self.dataset_path,
                model_path=self.model_path,
                metrics_path=self.metrics_path,
                progress=lambda percent, message: self.progress.emit(percent, message),
            )
        except Exception as exc:  # User-facing recovery must cover model/data failures.
            self.failed.emit(str(exc))
            return
        self.finished.emit(bundle)


class MainWindow(QMainWindow):
    """Main workbench for inputs, predictions, trends and model status."""

    def __init__(
        self,
        prediction_service: PredictionService | None = None,
        model_path: Path = DEFAULT_MODEL_PATH,
        dataset_path: Path = DEFAULT_DATASET_PATH,
        metrics_path: Path = DEFAULT_METRICS_PATH,
        auto_load_model: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("永磁同步电机 AI 设计助手")
        self.setMinimumSize(1040, 760)
        self.resize(1220, 900)

        self.model_path = model_path
        self.dataset_path = dataset_path
        self.metrics_path = metrics_path
        self.prediction_service = prediction_service
        self.load_error = ""
        self._training_thread: QThread | None = None
        self._training_worker: TrainingWorker | None = None
        if self.prediction_service is None and auto_load_model:
            self._try_load_default_model()

        self.inputs: dict[str, QDoubleSpinBox | QSpinBox] = {}
        self._build_interface()
        self._refresh_model_state()

    def _try_load_default_model(self) -> None:
        if not self.model_path.is_file():
            self.load_error = "模型尚未训练"
            return
        try:
            bundle = ModelBundle.load(self.model_path)
        except Exception as exc:  # A corrupt local artifact must be recoverable in the UI.
            self.load_error = f"模型加载失败：{exc}"
            return
        self.prediction_service = PredictionService(bundle)

    def _build_interface(self) -> None:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(14)
        layout.addWidget(self._build_hero())

        disclaimer = QLabel(
            "教学原型：预测由合成数据训练的随机森林给出。结果用于展示参数趋势，"
            "不能替代有限元计算、样机测试或正式工程设计结论。"
        )
        disclaimer.setObjectName("disclaimer")
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_design_tab(), "设计分析")
        self.tabs.addTab(self._build_model_tab(), "模型评估")
        self.tabs.addTab(self._build_environment_tab(), "开发环境")
        layout.addWidget(self.tabs, 1)

        footer = QLabel("Python · PyQt6 · OOP · Random Forest · 五种表贴式拓扑")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(footer)
        self.setCentralWidget(page)

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("hero")
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(24, 18, 24, 18)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        eyebrow = QLabel("PMSM DESIGN WORKBENCH")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("永磁同步电机 AI 设计助手")
        title.setObjectName("title")
        subtitle = QLabel("五种表贴式拓扑 · 客户参数快速性能预测")
        subtitle.setObjectName("subtitle")
        text_layout.addWidget(eyebrow)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)

        self.stage_label = QLabel("模型待训练")
        self.stage_label.setObjectName("stage")
        layout.addLayout(text_layout, 1)
        layout.addWidget(self.stage_label, 0, Qt.AlignmentFlag.AlignTop)
        return hero

    def _build_design_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(4, 10, 4, 4)
        layout.setSpacing(12)
        layout.addWidget(self._build_input_panel())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.torque_card = MetricCard("平均转矩", "N·m")
        self.ripple_card = MetricCard("转矩脉动估计", "%")
        self.efficiency_card = MetricCard("效率", "%")
        metrics.addWidget(self.torque_card)
        metrics.addWidget(self.ripple_card)
        metrics.addWidget(self.efficiency_card)
        right_layout.addLayout(metrics)

        self.prediction_message = QLabel("加载或训练模型后开始预测。")
        self.prediction_message.setObjectName("prediction-message")
        self.prediction_message.setWordWrap(True)
        right_layout.addWidget(self.prediction_message)

        trend_panel = QFrame()
        trend_panel.setObjectName("panel")
        trend_layout = QVBoxLayout(trend_panel)
        trend_layout.setContentsMargins(14, 12, 14, 12)
        trend_header = QHBoxLayout()
        trend_title = QLabel("参数扫描趋势")
        trend_title.setObjectName("section-title")
        trend_header.addWidget(trend_title)
        trend_header.addStretch(1)

        self.trend_parameter_combo = QComboBox()
        for spec in PARAMETER_SPECS:
            self.trend_parameter_combo.addItem(spec.label, spec.name)
        self.trend_parameter_combo.setCurrentIndex(
            self.trend_parameter_combo.findData("rated_current_a")
        )
        self.trend_output_combo = QComboBox()
        self.trend_output_combo.addItem("平均转矩", "torque_nm")
        self.trend_output_combo.addItem("转矩脉动", "torque_ripple_pct")
        self.trend_output_combo.addItem("效率", "efficiency_pct")
        self.trend_button = QPushButton("更新趋势")
        self.trend_button.clicked.connect(self.update_trend)
        trend_header.addWidget(self.trend_parameter_combo)
        trend_header.addWidget(self.trend_output_combo)
        trend_header.addWidget(self.trend_button)
        trend_layout.addLayout(trend_header)

        self.trend_canvas = TrendPlotCanvas()
        trend_layout.addWidget(self.trend_canvas)
        right_layout.addWidget(trend_panel, 1)
        layout.addWidget(right, 1)
        return tab

    def _build_input_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(430)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        input_scroll = QScrollArea()
        input_scroll.setObjectName("input-scroll")
        input_scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(8)

        title = QLabel("客户常用参数")
        title.setObjectName("section-title")
        caption = QLabel("先选择拓扑并填写额定设计点，复杂参数放在高级页。")
        caption.setObjectName("section-caption")
        caption.setWordWrap(True)
        content_layout.addWidget(title)
        content_layout.addWidget(caption)

        topology_label = QLabel("电机拓扑")
        topology_label.setObjectName("field-label")
        self.topology_combo = QComboBox()
        for topology in SPM_TOPOLOGIES:
            self.topology_combo.addItem(topology.label, topology.key)
        self.topology_combo.setCurrentIndex(
            self.topology_combo.findData(DEFAULT_DESIGN.topology)
        )
        self.topology_description = QLabel("")
        self.topology_description.setObjectName("section-caption")
        self.topology_description.setWordWrap(True)
        self.topology_combo.currentIndexChanged.connect(self._topology_changed)
        topology_row = QHBoxLayout()
        topology_row.setSpacing(8)
        topology_row.addWidget(topology_label)
        topology_row.addWidget(self.topology_combo, 1)
        content_layout.addLayout(topology_row)
        content_layout.addWidget(self.topology_description)

        self.input_tabs = QTabWidget()
        self.input_tabs.setObjectName("input-tabs")
        self.input_tabs.setMinimumHeight(300)
        basic_tab = QWidget()
        basic_form = self._build_parameter_form(BASIC_PARAMETER_NAMES)
        basic_tab.setLayout(basic_form)
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setContentsMargins(4, 6, 4, 6)
        advanced_layout.setSpacing(5)
        electrical_title = QLabel("电气参数")
        electrical_title.setObjectName("field-section-title")
        mechanical_title = QLabel("机械结构参数")
        mechanical_title.setObjectName("field-section-title")
        advanced_layout.addWidget(electrical_title)
        advanced_layout.addLayout(
            self._build_parameter_form(ADVANCED_ELECTRICAL_NAMES)
        )
        advanced_layout.addSpacing(4)
        advanced_layout.addWidget(mechanical_title)
        advanced_layout.addLayout(
            self._build_parameter_form(ADVANCED_MECHANICAL_NAMES)
        )
        advanced_layout.addStretch(1)
        self.input_tabs.addTab(basic_tab, "基础参数")
        self.input_tabs.addTab(advanced_tab, "高级参数")
        content_layout.addWidget(self.input_tabs)

        advanced_hint = QLabel(
            "高级页用于补充电气与机械结构数据；未修改时使用推荐默认值。"
        )
        advanced_hint.setObjectName("section-caption")
        advanced_hint.setWordWrap(True)
        content_layout.addWidget(advanced_hint)
        input_scroll.setWidget(scroll_content)
        layout.addWidget(input_scroll, 1)

        self.validation_label = QLabel("")
        self.validation_label.setObjectName("warning")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        self.model_status_label = QLabel("")
        self.model_status_label.setObjectName("model-status")
        self.model_status_label.setWordWrap(True)
        layout.addWidget(self.model_status_label)

        self.training_progress = QProgressBar()
        self.training_progress.setRange(0, 100)
        self.training_progress.setVisible(False)
        layout.addWidget(self.training_progress)

        self.train_button = QPushButton("一键训练模型")
        self.train_button.clicked.connect(self.start_training)
        layout.addWidget(self.train_button)

        self.predict_button = QPushButton("预测当前设计")
        self.predict_button.clicked.connect(self.predict_current_design)
        layout.addWidget(self.predict_button)
        self._topology_changed()
        return panel

    def _build_parameter_form(
        self,
        parameter_names: tuple[str, ...],
    ) -> QGridLayout:
        form = QGridLayout()
        form.setContentsMargins(4, 4, 4, 4)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(4)
        specs = {spec.name: spec for spec in PARAMETER_SPECS}
        for row, name in enumerate(parameter_names):
            spec = specs[name]
            label = QLabel(spec.label)
            label.setObjectName("field-label")
            if spec.is_integer:
                control = QSpinBox()
                control.setRange(int(spec.minimum), int(spec.maximum))
                control.setSingleStep(1)
            else:
                control = QDoubleSpinBox()
                control.setDecimals(spec.decimals)
                control.setRange(spec.minimum, spec.maximum)
                control.setSingleStep(spec.step)
            control.setValue(getattr(DEFAULT_DESIGN, spec.name))
            control.setMinimumWidth(110)
            self.inputs[spec.name] = control
            unit = QLabel(spec.unit)
            unit.setObjectName("field-unit")
            form.addWidget(label, row, 0)
            form.addWidget(control, row, 1)
            form.addWidget(unit, row, 2)
        form.setRowStretch(len(parameter_names), 1)
        return form

    def _topology_changed(self) -> None:
        topology_key = str(self.topology_combo.currentData())
        topology = next(item for item in SPM_TOPOLOGIES if item.key == topology_key)
        self.topology_description.setText(
            f"{topology.short_label} · {topology.pole_pairs} 对极。{topology.description}"
        )
        if hasattr(self, "validation_label"):
            self.validation_label.setText("")

    def _build_model_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("随机森林代理模型")
        title.setObjectName("section-title")
        self.model_train_button = QPushButton("重新训练")
        self.model_train_button.clicked.connect(self.start_training)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.model_train_button)
        layout.addLayout(header)

        self.model_summary_label = QLabel("")
        self.model_summary_label.setObjectName("section-caption")
        self.model_summary_label.setWordWrap(True)
        layout.addWidget(self.model_summary_label)

        content = QHBoxLayout()
        self.metrics_table = QTableWidget(0, 4)
        self.metrics_table.setHorizontalHeaderLabels(["拓扑 / 目标", "R²", "MAE", "RMSE"])
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.metrics_table.setMinimumWidth(390)
        self.importance_canvas = ImportancePlotCanvas()
        content.addWidget(self.metrics_table, 1)
        content.addWidget(self.importance_canvas, 2)
        layout.addLayout(content, 1)
        return tab

    def _build_environment_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 10, 8, 8)
        header = QHBoxLayout()
        title = QLabel("开发环境自检")
        title.setObjectName("section-title")
        caption = QLabel("只检查本地依赖，不访问网络")
        caption.setObjectName("section-caption")
        self.check_button = QPushButton("检查开发环境")
        self.check_button.clicked.connect(self.run_environment_check)
        header.addWidget(title)
        header.addWidget(caption)
        header.addStretch(1)
        header.addWidget(self.check_button)
        layout.addLayout(header)
        self.environment_output = QPlainTextEdit()
        self.environment_output.setReadOnly(True)
        self.environment_output.setPlaceholderText("点击“检查开发环境”查看结果。")
        layout.addWidget(self.environment_output)
        return tab

    def current_design(self) -> PMSMDesign:
        """Construct and validate a design from the current controls."""

        values: dict[str, float | int] = {}
        for spec in PARAMETER_SPECS:
            control = self.inputs[spec.name]
            values[spec.name] = int(control.value()) if spec.is_integer else float(control.value())
        design = PMSMDesign(
            topology=str(self.topology_combo.currentData()),
            **values,
        )
        design.validate()
        return design

    def predict_current_design(self) -> None:
        """Run the selected design through the loaded surrogate service."""

        self.validation_label.setText("")
        if self.prediction_service is None:
            self.validation_label.setText("请先训练或加载模型。")
            return
        try:
            design = self.current_design()
        except ValueError as exc:
            self.validation_label.setText(str(exc))
            return

        started = perf_counter()
        report = self.prediction_service.predict(design)
        elapsed_ms = (perf_counter() - started) * 1000.0
        self._display_prediction(report, design, elapsed_ms)
        self.update_trend()

    def _display_prediction(
        self,
        report: PredictionReport,
        design: PMSMDesign,
        elapsed_ms: float,
    ) -> None:
        self.torque_card.update_values(
            report.surrogate.torque_nm,
            report.analytical.torque_nm,
            "N·m",
        )
        self.ripple_card.update_values(
            report.surrogate.torque_ripple_pct,
            report.analytical.torque_ripple_pct,
            "%",
        )
        self.efficiency_card.update_values(
            report.surrogate.efficiency_pct,
            report.analytical.efficiency_pct,
            "%",
        )
        self.prediction_message.setText(
            self._prediction_summary(report, design, elapsed_ms)
        )

    @staticmethod
    def _prediction_summary(
        report: PredictionReport,
        design: PMSMDesign,
        elapsed_ms: float,
    ) -> str:
        delta_torque = abs(report.surrogate.torque_nm - report.analytical.torque_nm)
        delta_ripple = abs(
            report.surrogate.torque_ripple_pct - report.analytical.torque_ripple_pct
        )
        delta_efficiency = abs(
            report.surrogate.efficiency_pct - report.analytical.efficiency_pct
        )
        summary = (
            f"本次预测耗时 {elapsed_ms:.1f} ms；当前解析输出功率 "
            f"{report.analytical_power_w:.0f} W；"
            f"代理模型与公式差值：转矩 {delta_torque:.3f} N·m、"
            f"脉动 {delta_ripple:.3f} 个百分点、效率 {delta_efficiency:.3f} 个百分点。"
        )
        topology = next(item for item in SPM_TOPOLOGIES if item.key == design.topology)
        voltage_status = "满足" if report.voltage_feasible else "不满足"
        summary = (
            f"{topology.short_label}。"
            + summary
            + f" 相电压需求 {report.required_voltage_v:.1f} V"
            f" / 可用 {report.maximum_phase_voltage_v:.1f} V"
            f"（利用率 {report.voltage_utilization_pct:.1f}%，{voltage_status}）。"
        )
        if report.outside_training_power_range:
            summary += " 当前工况超出 300–3500 W 训练覆盖范围，不建议解释模型结果。"
        return summary

    def update_trend(self) -> None:
        """Refresh the selected parameter-scan chart."""

        if self.prediction_service is None:
            self.validation_label.setText("模型尚未就绪，不能生成趋势。")
            return
        try:
            design = self.current_design()
            parameter = str(self.trend_parameter_combo.currentData())
            output = str(self.trend_output_combo.currentData())
            series = self.prediction_service.scan(design, parameter, output)
        except ValueError as exc:
            self.validation_label.setText(str(exc))
            return
        self.trend_canvas.plot_series(series)

    def start_training(self) -> None:
        """Start the bundled-data training job in a background QThread."""

        if self._training_thread is not None:
            return
        self._set_training_state(True, "准备训练模型")
        thread = QThread(self)
        worker = TrainingWorker(
            dataset_path=self.dataset_path,
            model_path=self.model_path,
            metrics_path=self.metrics_path,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._training_progressed)
        worker.finished.connect(self._training_finished)
        worker.failed.connect(self._training_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._training_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._training_thread = thread
        self._training_worker = worker
        thread.start()

    def _training_progressed(self, percent: int, message: str) -> None:
        self.training_progress.setValue(percent)
        self.model_status_label.setText(message)

    def _training_finished(self, bundle: object) -> None:
        if isinstance(bundle, ModelBundle):
            self.prediction_service = PredictionService(bundle)
            self.load_error = ""
            self._refresh_model_state()
            self.model_status_label.setText("模型训练完成，可以开始预测。")
        else:
            self._training_failed("训练返回了无效模型")

    def _training_failed(self, message: str) -> None:
        self.load_error = message
        self.model_status_label.setText(f"训练失败：{message}")
        self.prediction_message.setText(f"训练失败：{message}")

    def _training_thread_finished(self) -> None:
        self._training_thread = None
        self._training_worker = None
        self._set_training_state(False, "")

    def _set_training_state(self, training: bool, message: str) -> None:
        self.training_progress.setVisible(training)
        if training:
            self.training_progress.setValue(0)
            self.model_status_label.setText(message)
        for button in (self.train_button, self.model_train_button, self.predict_button):
            button.setEnabled(not training)
        self.predict_button.setEnabled(not training and self.prediction_service is not None)

    def _refresh_model_state(self) -> None:
        ready = self.prediction_service is not None
        self.predict_button.setEnabled(ready)
        self.trend_button.setEnabled(ready)
        if ready:
            bundle = self.prediction_service.bundle
            self.stage_label.setText("模型已就绪")
            self.model_status_label.setText("随机森林模型已加载，可进行预测与参数扫描。")
            metadata = bundle.training_metadata
            self.model_summary_label.setText(
                f"{len(SPM_TOPOLOGIES)} 种拓扑共训练 {metadata['rows']} 条合成样本，"
                f"{metadata['estimators']} 棵树，最大深度 {metadata['max_depth']}。"
                "以下为各拓扑独立测试集指标；结果只验证对合成解析生成器的拟合。"
            )
            self._populate_metrics(bundle)
            self.importance_canvas.plot_importance(bundle.feature_importances)
        else:
            self.stage_label.setText("模型待训练")
            self.model_status_label.setText(self.load_error or "模型尚未训练")
            self.prediction_message.setText("点击“一键训练模型”构建随机森林代理模型。")
            self.model_summary_label.setText(
                "训练完成后展示独立测试集指标和平均特征重要性。"
            )
            self.metrics_table.setRowCount(0)
            self.importance_canvas.show_placeholder()
            self.torque_card.clear_values("N·m")
            self.ripple_card.clear_values("%")
            self.efficiency_card.clear_values("%")

    def _populate_metrics(self, bundle: ModelBundle) -> None:
        rows: list[tuple[str, str, str, str]] = []
        for topology in SPM_TOPOLOGIES:
            metrics = bundle.topology_metrics.get(topology.key, bundle.test_metrics)
            for metric in metrics:
                rows.append(
                    (
                        f"{topology.short_label} / {TARGET_LABELS[metric.target]}",
                        f"{metric.r2:.4f}",
                        f"{metric.mae:.4f}",
                        f"{metric.rmse:.4f}",
                    )
                )
        self.metrics_table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.metrics_table.setItem(row, column, item)
        self.metrics_table.resizeColumnsToContents()

    def run_environment_check(self) -> list[EnvironmentCheck]:
        """Run checks and display a local dependency report."""

        checks = collect_environment_checks()
        lines = [
            f"{'PASS' if check.passed else 'FAIL'}  {check.name}: {check.detail}"
            for check in checks
        ]
        passed_count = sum(check.passed for check in checks)
        result = "全部通过" if all_checks_passed(checks) else "存在待处理项"
        lines.extend(("", f"结果：{result}（{passed_count}/{len(checks)}）"))
        self.environment_output.setPlainText("\n".join(lines))
        return checks

    def closeEvent(self, event: QCloseEvent) -> None:
        """Prevent destroying a live training thread."""

        if self._training_thread is not None and self._training_thread.isRunning():
            self.validation_label.setText("模型正在训练，请等待完成后再关闭窗口。")
            event.ignore()
            return
        super().closeEvent(event)
