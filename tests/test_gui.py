"""Headless GUI smoke tests for the design workbench."""

from PyQt6.QtCore import Qt

from pmsm_ai.dataset import PMSMDesignDatasetGenerator
from pmsm_ai.ui.main_window import MainWindow


def test_main_window_contains_three_workbench_tabs(qtbot, tiny_service) -> None:
    window = MainWindow(prediction_service=tiny_service, auto_load_model=False)
    qtbot.addWidget(window)

    assert window.windowTitle() == "永磁同步电机 AI 设计助手"
    assert window.check_button.text() == "检查开发环境"
    assert window.environment_output.isReadOnly()
    assert window.tabs.count() == 3
    assert window.predict_button.isEnabled()


def test_prediction_button_updates_metrics_and_trend(qtbot, tiny_service) -> None:
    window = MainWindow(prediction_service=tiny_service, auto_load_model=False)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.predict_button, Qt.MouseButton.LeftButton)

    assert "N·m" in window.torque_card.value_label.text()
    assert "公式基准" in window.torque_card.baseline_label.text()
    assert "解析输出功率" in window.prediction_message.text()
    assert window.trend_canvas.figure.axes[0].lines


def test_environment_check_button_reports_results(qtbot, tiny_service) -> None:
    window = MainWindow(prediction_service=tiny_service, auto_load_model=False)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.check_button, Qt.MouseButton.LeftButton)

    output = window.environment_output.toPlainText()
    assert "PyQt6" in output
    assert "scikit-learn" in output
    assert "结果：" in output


def test_missing_model_disables_prediction(qtbot) -> None:
    window = MainWindow(auto_load_model=False)
    qtbot.addWidget(window)

    assert not window.predict_button.isEnabled()
    assert "尚未训练" in window.model_status_label.text()


def test_corrupt_model_is_reported_without_crashing(qtbot, tmp_path) -> None:
    model_path = tmp_path / "corrupt.joblib"
    model_path.write_bytes(b"not a joblib model")

    window = MainWindow(model_path=model_path, auto_load_model=True)
    qtbot.addWidget(window)

    assert "模型加载失败" in window.model_status_label.text()
    assert not window.predict_button.isEnabled()


def test_one_click_training_worker_completes(qtbot, tmp_path) -> None:
    dataset_path = tmp_path / "tiny.csv"
    PMSMDesignDatasetGenerator(seed=5).generate(160).to_csv(dataset_path, index=False)
    window = MainWindow(
        auto_load_model=False,
        model_path=tmp_path / "model.joblib",
        dataset_path=dataset_path,
        metrics_path=tmp_path / "metrics.json",
    )
    qtbot.addWidget(window)

    window.start_training()
    qtbot.waitUntil(lambda: window.prediction_service is not None, timeout=10000)

    assert (tmp_path / "model.joblib").is_file()
    assert (tmp_path / "metrics.json").is_file()
    assert window.predict_button.isEnabled()
