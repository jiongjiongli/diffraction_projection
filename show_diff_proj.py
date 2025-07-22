from pathlib import Path
from PIL import Image
import numpy as np
import sys
import fabio
from PySide6 import QtCore
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication,
                               QMainWindow,
                               QWidget,
                               QFileDialog,
                               QVBoxLayout,
                               QDialog,
                               QPushButton,
                               QLabel)
from matplotlib import patches
from matplotlib.backends.backend_qtagg import FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.colors import LogNorm


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)

class PlotDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Diffraction Profile")
        width = 500
        height = 400
        self.setFixedSize(width, height)

        # Layout
        layout = QVBoxLayout(self)

        self.canvas = MplCanvas(self, dpi=100)
        layout.addWidget(self.canvas)

        self.plot(data)

    def plot(self, data):
        ax = self.canvas.axes
        ax.cla()
        ax.set_xlabel("Column (Y in Image)")
        ax.set_ylabel("Pixel Sum")
        ax.set_title("Pixel Sum Along Each Column")
        ax.plot(data, label="Pixel Sum")
        ax.legend(loc="upper right")
        self.canvas.draw()


class DiffractionWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Window
        self.setWindowTitle("Diffraction Projection")
        width = 500
        height = 400
        self.setFixedSize(width, height)

        # Layout
        layout = QVBoxLayout()
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        # Show Image
        self.canvas = MplCanvas(self, dpi=100)
        ax = self.canvas.axes
        ax.set_title("Image")
        ax.axis('off')
        self.canvas.hide()
        layout.addWidget(self.canvas)

        layout.addStretch(1)

        # Show Projection Profile Button
        self.showProjBtn = QPushButton("Show Projection Profile")
        self.showProjBtn.clicked.connect(self.show_projection)
        self.showProjBtn.setEnabled(False)
        layout.addWidget(self.showProjBtn)

        # Quit Button
        quitBtn = QPushButton("Quit")
        quitBtn.clicked.connect(QApplication.quit)
        layout.addWidget(quitBtn)

        # Menu Bar
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')

        selectImageAction = QAction('Select an Image...', self)
        selectImageAction.setShortcut('Ctrl+I')
        selectImageAction.triggered.connect(self.browseFile)

        fileMenu.addAction(selectImageAction)

        # Rectangle draw events
        self.canvas.mpl_connect('button_press_event', self.imagePressed)
        self.canvas.mpl_connect('motion_notify_event', self.imageOnMotion)
        self.canvas.mpl_connect('button_release_event', self.imageReleased)

        # StatusBar
        self.statusbar = self.statusBar()
        self.coord_label = QLabel("Mouse: ")
        self.statusbar.addPermanentWidget(self.coord_label, 1)

        # Image Data
        self.image = None

        # Rectangle draw state
        self.start_point = None
        self.rect_patch = None
        self.last_rect_patch = None

    def imagePressed(self, event):
        if event.inaxes != self.canvas.axes:
            return

        if self.start_point is None:
            self.start_point = (event.xdata, event.ydata)
            x0, y0 = self.start_point
            # Show coordinates in status bar
            self.coord_label.setText(f"Rect: x0={int(x0)} y0={int(y0)}")
            self.showProjBtn.setEnabled(False)

            if self.last_rect_patch:
                self.last_rect_patch.remove()
                self.last_rect_patch = None
                self.canvas.draw_idle()
        else:
            end_point = (event.xdata, event.ydata)
            x0, y0 = self.start_point
            x1, y1 = end_point
            width, height = x1 - x0, y1 - y0
            self.last_rect_patch = patches.Rectangle(
                (x0, y0), width, height,
                linewidth=2, edgecolor='red', facecolor='none'
            )
            self.canvas.axes.add_patch(self.last_rect_patch)

            # Reset for next draw
            self.start_point = None

            if self.rect_patch:
                self.rect_patch.remove()
                self.rect_patch = None

            self.canvas.draw_idle()
            self.showProjBtn.setEnabled(True)

    def imageOnMotion(self, event):
        if event.inaxes != self.canvas.axes or not self.start_point:
            return

        end_point = (event.xdata, event.ydata)

        # Draw rectangle preview
        x0, y0 = self.start_point
        x1, y1 = end_point
        width, height = x1 - x0, y1 - y0

        # Show coordinates in status bar
        self.coord_label.setText(f"Rect: x0={int(x0)} y0={int(y0)}, x1={int(x1)}, y1={int(y1)}")

        if self.rect_patch:
            self.rect_patch.set_bounds(x0, y0, width, height)
        else:
            self.rect_patch = patches.Rectangle(
                (x0, y0), width, height,
                linewidth=1, edgecolor='red', facecolor='none'
            )
            self.canvas.axes.add_patch(self.rect_patch)

        self.canvas.draw_idle()

    def imageReleased(self, event):
        if event.inaxes != self.canvas.axes:
            return

    def browseFile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Select an image file",
            filter="Image Files (*.png *.jpeg *.tif *.tiff)"
        )

        if file_path:
            file_path = Path(file_path)

            if file_path.suffix.lower() in [".png", ".jpeg"]:
                self.image = np.array(Image.open(file_path))
            else:
                self.image = fabio.open(file_path).data

            ax = self.canvas.axes
            ax.cla()
            img = self.image.copy()
            if img.ndim == 2:
                # img = img - (img.min() + 1)
                img = (img - np.min(img)) / (np.max(img) - np.min(img))
                ax.imshow(img, cmap='gray')
                # ax.imshow(img, cmap='gray', norm=LogNorm(vmin=img.min(), vmax=img.max()))
            else:
                ax.imshow(img)

            self.canvas.draw()
            self.canvas.show()
            self.coord_label.setText("Mouse: ")
            self.showProjBtn.setEnabled(False)
        else:
            print("No file selected.")

    def show_projection(self):
        if self.image is None or self.last_rect_patch is None:
            return

        img = self.image.copy()

        if img.ndim > 2:
            img = np.array(Image.fromarray(img).convert("L"))

        points = self.last_rect_patch.get_bbox().get_points()
        x0 = int(min(points[:, 0]))
        x1 = int(max(points[:, 0]))
        y0 = int(min(points[:, 1]))
        y1 = int(max(points[:, 1]))

        region = img[y0:y1, x0:x1]
        pixel_sums = np.sum(region.astype(np.float32), axis=1)
        dialog = PlotDialog(self, pixel_sums)
        dialog.exec()

app = QApplication(sys.argv)
window = DiffractionWindow()
window.show()
app.exec()
