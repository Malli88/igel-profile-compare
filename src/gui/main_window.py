"""Main Window for IGEL Profile Compare & Migration Tool.

Provides the primary user interface for comparing and migrating IGEL profiles.
"""

import sys
from pathlib import Path
from typing import Optional, List, Set
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QPushButton, QLabel, QLineEdit, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QProgressBar, QStatusBar, QToolBar, QComboBox,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QScrollArea, QFrame, QApplication,
    QStyle, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QColor, QBrush, QFont, QKeySequence

from src.core.ipm_handler import IPMHandler, IPMProfile, IPMValidationError
from src.core.comparator import ProfileComparator, ComparisonResult, DiffEntry, DiffType
from src.core.migrator import (
    ProfileMigrator, MigrationDirection, MigrationMode,
    MigrationPlan, MigrationResult
)
from src.utils.logger import get_logger


# Color scheme for diff types
COLORS = {
    DiffType.LEFT_ONLY: QColor(255, 200, 200),      # Light red
    DiffType.RIGHT_ONLY: QColor(200, 255, 200),     # Light green
    DiffType.EQUAL: QColor(255, 255, 255),          # White
    DiffType.DIFFERENT: QColor(255, 255, 200),      # Light yellow
    DiffType.TYPE_MISMATCH: QColor(255, 200, 255),  # Light purple
}


class LoadProfileWorker(QThread):
    """Worker thread for loading profiles."""
    finished = pyqtSignal(object, str)  # profile, error_message
    progress = pyqtSignal(str)

    def __init__(self, file_path: str, handler: IPMHandler):
        super().__init__()
        self.file_path = file_path
        self.handler = handler

    def run(self):
        try:
            self.progress.emit(f"Loading {Path(self.file_path).name}...")
            profile = self.handler.load_profile(self.file_path)
            self.finished.emit(profile, "")
        except IPMValidationError as e:
            self.finished.emit(None, str(e))
        except Exception as e:
            self.finished.emit(None, f"Unexpected error: {str(e)}")


class CompareWorker(QThread):
    """Worker thread for comparing profiles."""
    finished = pyqtSignal(object)  # ComparisonResult
    progress = pyqtSignal(str)

    def __init__(self, left: IPMProfile, right: IPMProfile, comparator: ProfileComparator):
        super().__init__()
        self.left = left
        self.right = right
        self.comparator = comparator

    def run(self):
        self.progress.emit("Comparing profiles...")
        result = self.comparator.compare(self.left, self.right)
        self.finished.emit(result)


class MigrationPreviewDialog(QDialog):
    """Dialog for previewing migration changes."""

    def __init__(self, plan: MigrationPlan, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.setWindowTitle("Migration Preview")
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Summary
        summary = self.plan.summary()
        summary_label = QLabel(
            f"<b>Migration Summary:</b><br>"
            f"Total changes: {summary['total']}<br>"
            f"New keys to add: {summary['adds']}<br>"
            f"Values to update: {summary['updates']}<br>"
            f"Type changes: {summary['type_changes']}"
        )
        layout.addWidget(summary_label)

        # Changes list
        changes_group = QGroupBox("Planned Changes")
        changes_layout = QVBoxLayout(changes_group)

        changes_text = QTextEdit()
        changes_text.setReadOnly(True)
        changes_text.setFont(QFont("Consolas", 9))

        text_lines = []
        for action in self.plan.actions:
            text_lines.append(action.describe())
        changes_text.setPlainText("\n".join(text_lines))

        changes_layout.addWidget(changes_text)
        layout.addWidget(changes_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class ProfilePanel(QGroupBox):
    """Panel for displaying profile information."""

    file_loaded = pyqtSignal(str)  # Emits file path when loaded

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.profile: Optional[IPMProfile] = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # File selection row
        file_row = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file loaded")
        file_row.addWidget(self.file_path_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_row.addWidget(self.browse_btn)

        layout.addLayout(file_row)

        # Info labels
        self.info_label = QLabel("Load a profile to see details")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select IPM Profile",
            "",
            "IPM Files (*.ipm);;All Files (*)"
        )
        if file_path:
            self.file_loaded.emit(file_path)

    def set_profile(self, profile: IPMProfile):
        self.profile = profile
        self.file_path_edit.setText(str(profile.file_path))
        self.info_label.setText(
            f"<b>Files:</b> {len(profile.files)}<br>"
            f"<b>JSON configs:</b> {len(profile.json_configs)}<br>"
            f"<b>Configuration keys:</b> {len(profile.flattened_config)}<br>"
            f"<b>Loaded:</b> {profile.load_timestamp.strftime(' %Y-%m-%d %H:%M:%S') if profile.load_timestamp else 'N/A'}"
        )

    def clear(self):
        self.profile = None
        self.file_path_edit.clear()
        self.info_label.setText("Load a profile to see details")


class FilterPanel(QGroupBox):
    """Panel for search and filter controls."""

    filter_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Search & Filter", parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Search row
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to search keys or values...")
        self.search_edit.textChanged.connect(self._on_filter_changed)
        search_row.addWidget(self.search_edit)

        self.search_keys_cb = QCheckBox("Keys")
        self.search_keys_cb.setChecked(True)
        self.search_keys_cb.stateChanged.connect(self._on_filter_changed)
        search_row.addWidget(self.search_keys_cb)

        self.search_values_cb = QCheckBox("Values")
        self.search_values_cb.setChecked(True)
        self.search_values_cb.stateChanged.connect(self._on_filter_changed)
        search_row.addWidget(self.search_values_cb)

        layout.addLayout(search_row)

        # Filter checkboxes row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Show:"))

        self.show_left_only = QCheckBox("Left Only")
        self.show_left_only.setChecked(True)
        self.show_left_only.stateChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.show_left_only)

        self.show_right_only = QCheckBox("Right Only")
        self.show_right_only.setChecked(True)
        self.show_right_only.stateChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.show_right_only)

        self.show_equal = QCheckBox("Equal")
        self.show_equal.setChecked(False)  # Hidden by default
        self.show_equal.stateChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.show_equal)

        self.show_different = QCheckBox("Different")
        self.show_different.setChecked(True)
        self.show_different.stateChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.show_different)

        filter_row.addStretch()
        layout.addLayout(filter_row)

    def _on_filter_changed(self):
        self.filter_changed.emit()

    def get_filter_settings(self) -> dict:
        return {
            'search_text': self.search_edit.text(),
            'search_in_keys': self.search_keys_cb.isChecked(),
            'search_in_values': self.search_values_cb.isChecked(),
            'show_left_only': self.show_left_only.isChecked(),
            'show_right_only': self.show_right_only.isChecked(),
            'show_equal': self.show_equal.isChecked(),
            'show_different': self.show_different.isChecked(),
        }


class ComparisonTable(QTableWidget):
    """Table widget for displaying comparison results."""

    selection_changed = pyqtSignal(set)  # Emits set of selected keys

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries: List[DiffEntry] = []
        self.setup_ui()

    def setup_ui(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Key", "Left Value", "Right Value", "Status"])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)

        self.itemSelectionChanged.connect(self._on_selection_changed)

    def set_entries(self, entries: List[DiffEntry]):
        self.entries = entries
        self.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            # Key
            key_item = QTableWidgetItem(entry.key)
            key_item.setData(Qt.ItemDataRole.UserRole, entry)
            self.setItem(row, 0, key_item)

            # Left value
            left_item = QTableWidgetItem(entry.get_display_left())
            self.setItem(row, 1, left_item)

            # Right value
            right_item = QTableWidgetItem(entry.get_display_right())
            self.setItem(row, 2, right_item)

            # Status
            status_text = {
                DiffType.LEFT_ONLY: "← Left Only",
                DiffType.RIGHT_ONLY: "Right Only →",
                DiffType.EQUAL: "Equal",
                DiffType.DIFFERENT: "Different",
                DiffType.TYPE_MISMATCH: "Type Mismatch",
            }.get(entry.diff_type, "Unknown")
            status_item = QTableWidgetItem(status_text)
            self.setItem(row, 3, status_item)

            # Set row color
            color = COLORS.get(entry.diff_type, QColor(255, 255, 255))
            for col in range(4):
                self.item(row, col).setBackground(QBrush(color))

    def _on_selection_changed(self):
        selected_keys = set()
        for item in self.selectedItems():
            if item.column() == 0:  # Key column
                entry = item.data(Qt.ItemDataRole.UserRole)
                if entry:
                    selected_keys.add(entry.key)
        self.selection_changed.emit(selected_keys)

    def get_selected_keys(self) -> Set[str]:
        selected = set()
        for row in range(self.rowCount()):
            if self.item(row, 0).isSelected():
                entry = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if entry:
                    selected.add(entry.key)
        return selected

    def select_all_different(self):
        self.clearSelection()
        for row in range(self.rowCount()):
            entry = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if entry and entry.diff_type in (DiffType.LEFT_ONLY, DiffType.RIGHT_ONLY, 
                                              DiffType.DIFFERENT, DiffType.TYPE_MISMATCH):
                self.selectRow(row)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.ipm_handler = IPMHandler()
        self.comparator = ProfileComparator()
        self.migrator = ProfileMigrator()

        self.left_profile: Optional[IPMProfile] = None
        self.right_profile: Optional[IPMProfile] = None
        self.comparison_result: Optional[ComparisonResult] = None

        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_statusbar()

        self.logger.info("Main window initialized")

    def setup_ui(self):
        self.setWindowTitle("IGEL Profile Compare & Migration Tool")
        self.setMinimumSize(1200, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Top section: Profile panels
        profiles_layout = QHBoxLayout()

        self.left_panel = ProfilePanel("Left Profile")
        self.left_panel.file_loaded.connect(lambda p: self.load_profile(p, "left"))
        profiles_layout.addWidget(self.left_panel)

        self.right_panel = ProfilePanel("Right Profile")
        self.right_panel.file_loaded.connect(lambda p: self.load_profile(p, "right"))
        profiles_layout.addWidget(self.right_panel)

        main_layout.addLayout(profiles_layout)

        # Compare button
        compare_row = QHBoxLayout()
        compare_row.addStretch()
        self.compare_btn = QPushButton("Compare Profiles")
        self.compare_btn.setEnabled(False)
        self.compare_btn.clicked.connect(self.compare_profiles)
        self.compare_btn.setMinimumWidth(200)
        compare_row.addWidget(self.compare_btn)
        compare_row.addStretch()
        main_layout.addLayout(compare_row)

        # Filter panel
        self.filter_panel = FilterPanel()
        self.filter_panel.filter_changed.connect(self.apply_filters)
        self.filter_panel.setEnabled(False)
        main_layout.addWidget(self.filter_panel)

        # Comparison results
        results_group = QGroupBox("Comparison Results")
        results_layout = QVBoxLayout(results_group)

        # Summary label
        self.summary_label = QLabel("Load two profiles and click Compare to see results")
        results_layout.addWidget(self.summary_label)

        # Results table
        self.results_table = ComparisonTable()
        self.results_table.selection_changed.connect(self.on_selection_changed)
        results_layout.addWidget(self.results_table)

        main_layout.addWidget(results_group, stretch=1)

        # Migration controls
        migration_group = QGroupBox("Migration")
        migration_layout = QHBoxLayout(migration_group)

        migration_layout.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Left → Right", MigrationDirection.LEFT_TO_RIGHT)
        self.direction_combo.addItem("Right → Left", MigrationDirection.RIGHT_TO_LEFT)
        migration_layout.addWidget(self.direction_combo)

        migration_layout.addSpacing(20)

        self.select_all_btn = QPushButton("Select All Different")
        self.select_all_btn.clicked.connect(self.results_table.select_all_different)
        self.select_all_btn.setEnabled(False)
        migration_layout.addWidget(self.select_all_btn)

        self.selection_label = QLabel("0 keys selected")
        migration_layout.addWidget(self.selection_label)

        migration_layout.addStretch()

        self.preview_btn = QPushButton("Preview Migration")
        self.preview_btn.clicked.connect(self.preview_migration)
        self.preview_btn.setEnabled(False)
        migration_layout.addWidget(self.preview_btn)

        self.migrate_btn = QPushButton("Migrate Selected")
        self.migrate_btn.clicked.connect(self.execute_migration)
        self.migrate_btn.setEnabled(False)
        migration_layout.addWidget(self.migrate_btn)

        main_layout.addWidget(migration_group)

    def setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_left = QAction("Open &Left Profile...", self)
        open_left.setShortcut(QKeySequence("Ctrl+L"))
        open_left.triggered.connect(lambda: self.left_panel.browse_file())
        file_menu.addAction(open_left)

        open_right = QAction("Open &Right Profile...", self)
        open_right.setShortcut(QKeySequence("Ctrl+R"))
        open_right.triggered.connect(lambda: self.right_panel.browse_file())
        file_menu.addAction(open_right)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        logs_action = QAction("Open &Logs Folder", self)
        logs_action.triggered.connect(self.open_logs_folder)
        help_menu.addAction(logs_action)

    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Using text buttons since we don't have icons
        open_left_btn = QPushButton("📂 Left")
        open_left_btn.clicked.connect(lambda: self.left_panel.browse_file())
        toolbar.addWidget(open_left_btn)

        open_right_btn = QPushButton("📂 Right")
        open_right_btn.clicked.connect(lambda: self.right_panel.browse_file())
        toolbar.addWidget(open_right_btn)

        toolbar.addSeparator()

        compare_btn = QPushButton("🔍 Compare")
        compare_btn.clicked.connect(self.compare_profiles)
        toolbar.addWidget(compare_btn)

    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)

        self.statusbar.showMessage("Ready")

    def load_profile(self, file_path: str, side: str):
        self.statusbar.showMessage(f"Loading {Path(file_path).name}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        worker = LoadProfileWorker(file_path, self.ipm_handler)
        worker.finished.connect(lambda p, e: self.on_profile_loaded(p, e, side))
        worker.start()

        # Keep reference to prevent garbage collection
        if side == "left":
            self._left_worker = worker
        else:
            self._right_worker = worker

    def on_profile_loaded(self, profile: Optional[IPMProfile], error: str, side: str):
        self.progress_bar.setVisible(False)

        if error:
            QMessageBox.critical(self, "Error Loading Profile", error)
            self.statusbar.showMessage("Failed to load profile")
            return

        if side == "left":
            self.left_profile = profile
            self.left_panel.set_profile(profile)
        else:
            self.right_profile = profile
            self.right_panel.set_profile(profile)

        self.statusbar.showMessage(f"Loaded {profile.file_path.name}")

        # Enable compare button if both profiles loaded
        self.compare_btn.setEnabled(
            self.left_profile is not None and self.right_profile is not None
        )

        # Clear previous comparison
        self.comparison_result = None
        self.results_table.setRowCount(0)
        self.filter_panel.setEnabled(False)

    def compare_profiles(self):
        if not self.left_profile or not self.right_profile:
            return

        self.statusbar.showMessage("Comparing profiles...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        worker = CompareWorker(self.left_profile, self.right_profile, self.comparator)
        worker.finished.connect(self.on_comparison_complete)
        worker.start()
        self._compare_worker = worker

    def on_comparison_complete(self, result: ComparisonResult):
        self.progress_bar.setVisible(False)
        self.comparison_result = result

        # Update summary
        summary = result.summary
        self.summary_label.setText(
            f"<b>Total keys:</b> {summary['total']} | "
            f"<b>Left only:</b> {summary['left_only']} | "
            f"<b>Right only:</b> {summary['right_only']} | "
            f"<b>Equal:</b> {summary['equal']} | "
            f"<b>Different:</b> {summary['different']}"
        )

        # Enable controls
        self.filter_panel.setEnabled(True)
        self.select_all_btn.setEnabled(True)

        # Apply filters and show results
        self.apply_filters()

        self.statusbar.showMessage(
            f"Comparison complete: {summary['total']} keys analyzed"
        )

    def apply_filters(self):
        if not self.comparison_result:
            return

        settings = self.filter_panel.get_filter_settings()
        filtered = self.comparator.filter_entries(
            self.comparison_result,
            search_text=settings['search_text'],
            show_left_only=settings['show_left_only'],
            show_right_only=settings['show_right_only'],
            show_equal=settings['show_equal'],
            show_different=settings['show_different'],
            search_in_keys=settings['search_in_keys'],
            search_in_values=settings['search_in_values']
        )

        self.results_table.set_entries(filtered)
        self.statusbar.showMessage(f"Showing {len(filtered)} of {len(self.comparison_result.entries)} entries")

    def on_selection_changed(self, selected_keys: Set[str]):
        count = len(selected_keys)
        self.selection_label.setText(f"{count} keys selected")
        self.preview_btn.setEnabled(count > 0)
        self.migrate_btn.setEnabled(count > 0)

    def preview_migration(self):
        selected_keys = self.results_table.get_selected_keys()
        if not selected_keys:
            QMessageBox.information(self, "No Selection", "Please select keys to migrate.")
            return

        direction = self.direction_combo.currentData()
        plan = self.migrator.create_migration_plan(
            self.comparison_result,
            direction,
            selected_keys,
            MigrationMode.SELECTED_ONLY
        )

        dialog = MigrationPreviewDialog(plan, self)
        dialog.exec()

    def execute_migration(self):
        selected_keys = self.results_table.get_selected_keys()
        if not selected_keys:
            QMessageBox.information(self, "No Selection", "Please select keys to migrate.")
            return

        direction = self.direction_combo.currentData()
        plan = self.migrator.create_migration_plan(
            self.comparison_result,
            direction,
            selected_keys,
            MigrationMode.SELECTED_ONLY
        )

        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Migration",
            f"This will modify {plan.total_actions} configuration values.\n\n"
            f"A backup will be created before making changes.\n\n"
            f"Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Ask for output file
        target = plan.target_profile.file_path
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Modified Profile",
            str(target.parent / f"{target.stem}_modified.ipm"),
            "IPM Files (*.ipm)"
        )

        if not output_path:
            return

        # Execute migration
        self.statusbar.showMessage("Executing migration...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        result = self.migrator.execute_migration(plan, Path(output_path))

        self.progress_bar.setVisible(False)

        if result.success:
            QMessageBox.information(
                self,
                "Migration Complete",
                f"Migration completed successfully!\n\n"
                f"Output file: {result.output_path}\n"
                f"Backup file: {result.backup_path}"
            )
            self.statusbar.showMessage("Migration completed successfully")
        else:
            QMessageBox.critical(
                self,
                "Migration Failed",
                f"Migration failed: {result.error_message}"
            )
            self.statusbar.showMessage("Migration failed")

    def show_about(self):
        QMessageBox.about(
            self,
            "About IGEL Profile Compare",
            "<h2>IGEL Profile Compare & Migration Tool</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A tool for comparing and migrating configuration settings "
            "between IGEL Profile Export (.ipm) files.</p>"
            "<p>© 2024 Stephan Mallmann</p>"
        )

    def open_logs_folder(self):
        import subprocess
        import os

        log_dir = self.logger.get_log_directory()
        if os.name == 'nt':
            os.startfile(log_dir)
        else:
            subprocess.run(['xdg-open', str(log_dir)])

    def closeEvent(self, event):
        self.logger.info("Application closing")
        self.ipm_handler.cleanup()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
