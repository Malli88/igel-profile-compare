"""Main application window."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QTreeWidget, QTreeWidgetItem, QSplitter,
    QMessageBox, QCheckBox, QLineEdit, QGroupBox, QStatusBar,
    QHeaderView, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from core.ipm_handler import load_ipm, IPMProfile
from core.comparator import compare_profiles, ComparisonResult
from core.migrator import migrate_settings


class ProfilePanel(QGroupBox):
    """Panel for loading and displaying a profile."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.profile: IPMProfile = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Load button and file label
        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load IPM File...")
        self.load_btn.clicked.connect(self._load_file)
        btn_layout.addWidget(self.load_btn)
        
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color: gray; font-style: italic;")
        btn_layout.addWidget(self.file_label, 1)
        layout.addLayout(btn_layout)
        
        # Profile info
        self.info_label = QLabel("")
        layout.addWidget(self.info_label)
    
    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open IPM File", "", "IPM Files (*.ipm);;All Files (*)"
        )
        if path:
            try:
                self.profile = load_ipm(path)
                self.file_label.setText(os.path.basename(path))
                self.file_label.setStyleSheet("color: black; font-weight: bold;")
                self.info_label.setText(
                    f"Profile: {self.profile.name}\n"
                    f"Settings: {len(self.profile.get_flat_settings())}"
                )
                self.parent().parent().on_profile_loaded()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")


class ComparisonTree(QTreeWidget):
    """Tree widget for displaying comparison results."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Setting", "Left Value", "Right Value", "Status"])
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    
    def load_comparison(self, result: ComparisonResult):
        self.clear()
        
        # Different values
        if result.different:
            diff_root = QTreeWidgetItem(["Different Values", "", "", str(len(result.different))])
            diff_root.setBackground(0, QBrush(QColor(255, 255, 200)))
            self.addTopLevelItem(diff_root)
            for key, (left, right) in sorted(result.different.items()):
                item = QTreeWidgetItem([key, str(left["value"]), str(right["value"]), "≠"])
                item.setCheckState(0, Qt.CheckState.Unchecked)
                item.setData(0, Qt.ItemDataRole.UserRole, ("different", key))
                diff_root.addChild(item)
            diff_root.setExpanded(True)
        
        # Only in left
        if result.only_left:
            left_root = QTreeWidgetItem([f"Only in {result.left_name}", "", "", str(len(result.only_left))])
            left_root.setBackground(0, QBrush(QColor(200, 255, 200)))
            self.addTopLevelItem(left_root)
            for key, val in sorted(result.only_left.items()):
                item = QTreeWidgetItem([key, str(val["value"]), "-", "←"])
                item.setCheckState(0, Qt.CheckState.Unchecked)
                item.setData(0, Qt.ItemDataRole.UserRole, ("only_left", key))
                left_root.addChild(item)
        
        # Only in right
        if result.only_right:
            right_root = QTreeWidgetItem([f"Only in {result.right_name}", "", "", str(len(result.only_right))])
            right_root.setBackground(0, QBrush(QColor(200, 200, 255)))
            self.addTopLevelItem(right_root)
            for key, val in sorted(result.only_right.items()):
                item = QTreeWidgetItem([key, "-", str(val["value"]), "→"])
                item.setData(0, Qt.ItemDataRole.UserRole, ("only_right", key))
                right_root.addChild(item)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IGEL Profile Compare & Migrate")
        self.setMinimumSize(1200, 700)
        self.comparison_result: ComparisonResult = None
        self._setup_ui()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Profile panels
        panels_layout = QHBoxLayout()
        self.left_panel = ProfilePanel("Left Profile (Source)")
        self.right_panel = ProfilePanel("Right Profile (Target)")
        panels_layout.addWidget(self.left_panel)
        panels_layout.addWidget(self.right_panel)
        layout.addLayout(panels_layout)
        
        # Compare button
        self.compare_btn = QPushButton("Compare Profiles")
        self.compare_btn.setEnabled(False)
        self.compare_btn.clicked.connect(self._compare)
        layout.addWidget(self.compare_btn)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter settings...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_edit)
        layout.addLayout(filter_layout)
        
        # Comparison tree
        self.tree = ComparisonTree()
        layout.addWidget(self.tree, 1)
        
        # Migration buttons
        btn_layout = QHBoxLayout()
        self.migrate_btn = QPushButton("Migrate Selected to Target →")
        self.migrate_btn.setEnabled(False)
        self.migrate_btn.clicked.connect(self._migrate)
        btn_layout.addWidget(self.migrate_btn)
        layout.addLayout(btn_layout)
        
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Load two IPM files to compare")
    
    def on_profile_loaded(self):
        """Called when a profile is loaded."""
        if self.left_panel.profile and self.right_panel.profile:
            self.compare_btn.setEnabled(True)
            self.status.showMessage("Ready to compare")
    
    def _compare(self):
        """Compare the loaded profiles."""
        try:
            self.comparison_result = compare_profiles(
                self.left_panel.profile,
                self.right_panel.profile
            )
            self.tree.load_comparison(self.comparison_result)
            self.migrate_btn.setEnabled(True)
            self.status.showMessage(self.comparison_result.summary)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Comparison failed:\n{e}")
    
    def _apply_filter(self, text: str):
        """Filter tree items."""
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            visible_children = 0
            for j in range(parent.childCount()):
                child = parent.child(j)
                matches = text.lower() in child.text(0).lower()
                child.setHidden(not matches)
                if matches:
                    visible_children += 1
            parent.setHidden(visible_children == 0 and text)
    
    def _migrate(self):
        """Migrate selected settings."""
        selected_keys = []
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    data = child.data(0, Qt.ItemDataRole.UserRole)
                    if data and data[0] in ("different", "only_left"):
                        selected_keys.append(data[1])
        
        if not selected_keys:
            QMessageBox.warning(self, "No Selection", "Please check settings to migrate.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Migrated Profile", "", "IPM Files (*.ipm)"
        )
        if path:
            try:
                migrate_settings(
                    self.left_panel.profile,
                    self.right_panel.profile,
                    selected_keys,
                    path
                )
                QMessageBox.information(self, "Success", f"Migrated {len(selected_keys)} settings to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Migration failed:\n{e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
