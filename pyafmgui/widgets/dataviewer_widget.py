import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
from pyqtgraph.parametertree import Parameter, ParameterTree

import pyafmgui.const as cts

class DataViewerWidget(QtGui.QWidget):
    def __init__(self, session, parent=None):
        super(DataViewerWidget, self).__init__(parent)
        self.session = session
        self.session.data_viewer_widget = self
        self.init_gui()
        self.updateTable()

    def init_gui(self):
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.tree = QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["File Id"])
        self.tree.currentItemChanged.connect(self.updatePlots)

        self.metadata_tree = pg.DataTreeWidget(data="No loaded data")

        self.params = Parameter.create(name='params', children=cts.data_viewer_params)

        self.curve_x = self.params.child('Display Options').child('Curve X axis')
        self.curve_x.sigValueChanged.connect(self.updateCurve)
        self.curve_y = self.params.child('Display Options').child('Curve Y axis')
        self.curve_y.sigValueChanged.connect(self.updateCurve)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)

        self.l = pg.GraphicsLayoutWidget()

        ## Add 3 plots into the first row (automatic position)
        self.plotItem = pg.PlotItem(lockAspect=True)
        vb = self.plotItem.getViewBox()
        vb.setAspectLocked(lock=True, ratio=1)

        self.ROI = pg.ROI([0,0], [1,1], movable=False, rotatable=False, resizable=False, removable=False, aspectLocked=True)
        self.ROI.setPen("r", linewidht=2)
        self.ROI.setZValue(10)

        self.correlogram = pg.ImageItem(lockAspect=True, autoDownsample=False)

        self.plotItem.addItem(self.correlogram)    # display correlogram

        colorMap = pg.colormap.get('afmhot', source='matplotlib', skipCache=True)     # choose perceptually uniform, diverging color map
        # generate an adjustabled color bar, initially spanning -1 to 1:
        self.bar = pg.ColorBarItem(
            interactive=False, values=(0,0), cmap=colorMap) 
        # link color bar and color map to correlogram, and show it in plotItem:
        self.bar.setImageItem(self.correlogram, insert_in=self.plotItem)

        self.p1 = pg.PlotItem()

        ## Put vertical label on left side
        layout.addWidget(self.tree, 0, 0, 1, 1)
        layout.addWidget(self.metadata_tree, 0, 1, 1, 1)
        layout.addWidget(self.paramTree, 0, 2, 1, 1)
        layout.addWidget(self.l, 1, 0, 1, 3)
        layout.setColumnStretch(1, 4)
    
    def mouseMoved(self,event):
        vb = self.plotItem.vb
        scene_coords = event.scenePos()
        if self.correlogram.sceneBoundingRect().contains(scene_coords):
            items = vb.mapSceneToView(event.scenePos())
            pixels = vb.mapFromViewToItem(self.correlogram, items)
            x, y = int(pixels.x()), int(pixels.y())
            self.ROI.setPos(x, y)
            self.session.current_curve_index = self.session.map_coords[x,y]
            self.updateCurve()
            if self.session.hertz_fit_widget:
                self.session.hertz_fit_widget.updatePlots()

    def closeEvent(self, evnt):
        self.session.data_viewer_widget = None
    
    def clear(self):
        self.tree.clear()
        self.updatePlots(None)
        self.metadata_tree.setData(data="No loaded data")
    
    def updateTable(self):
        filelist = self.session.loaded_files
        items = [QtWidgets.QTreeWidgetItem([file_id]) for file_id in filelist.keys()]
        self.tree.insertTopLevelItems(0, items)
        self.updatePlots()
    
    def get_sumary_metadata():
        pass
    
    def make_plot(self, force_curve):
        self.p1.clear()
        self.p1.showGrid(x=True, y=True)
        self.p1.enableAutoRange()
        self.p1.addLegend((100, 30))
        xkey = self.curve_x.value()
        ykey = self.curve_y.value()
        t0 = 0
        fc_segments = force_curve.get_segments()
        n_segments = len(fc_segments)
        for i, (seg_id, segment) in enumerate(fc_segments):
            x = getattr(segment, xkey)
            if xkey == "time":
                x = x + t0
                t0 = x[-1]
            y = getattr(segment, ykey)
            self.p1.plot(x, y, pen=(i,n_segments), name=f"{segment.segment_type} {seg_id}")
        self.p1.setLabel('left', ykey)
        self.p1.setLabel('bottom', xkey)
        self.p1.setTitle(f"{ykey}-{xkey}")
    
    def updateCurve(self):
        idx = self.session.current_curve_index
        height_channel = self.session.current_file.filemetadata['height_channel_key']
        if self.session.global_involts is None:
            deflection_sens = self.session.current_file.filemetadata['defl_sens_nmbyV']
        else:
            deflection_sens = self.session.global_involts
        force_curve = self.session.current_file.getcurve(idx)
        force_curve.preprocess_force_curve(deflection_sens, height_channel)
        if self.session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
            force_curve.shift_height()
        self.make_plot(force_curve)
    
    def updatePlots(self, item=None):
        if item is not None:
            file_id = item.text(0)
        elif self.tree.itemAt(0,0):
            self.tree.itemAt(0,0).setSelected(True)
            file_id = self.tree.itemAt(0,0).text(0)
        else:
            self.l.clear()
            return

        self.l.clear()

        self.session.current_file = self.session.loaded_files[file_id]

        if self.session.current_file.isFV:
            self.l.addItem(self.plotItem)
            self.plotItem.setTitle("piezo height")
            self.plotItem.setLabel('left', 'y pixels')
            self.plotItem.setLabel('bottom', 'x pixels')
            self.plotItem.addItem(self.ROI)
            self.plotItem.scene().sigMouseClicked.connect(self.mouseMoved)
            # create transform to center the corner element on the origin, for any assigned image:
            self.correlogram.setImage(self.session.current_file.piezoimg)
            self.bar.setLevels((self.session.current_file.piezoimg.min(), self.session.current_file.piezoimg.max()))
            rows, cols = self.session.current_file.piezoimg.shape
            self.plotItem.setXRange(0, cols)
            self.plotItem.setYRange(0, rows)
            curve_coords = np.arange(cols*rows).reshape((cols, rows))
            if self.session.current_file.filemetadata['file_type'] == "jpk-force-map":
                curve_coords = np.asarray([row[::(-1)**i] for i, row in enumerate(curve_coords)])
            self.session.map_coords = curve_coords
            self.l.ci.layout.setColumnStretchFactor(1, 2)

        self.l.addItem(self.p1)

        self.metadata_tree.setData(self.session.current_file.filemetadata)
        
        self.session.current_curve_index = 0
        self.ROI.setPos(0, 0)
        self.updateCurve()

        if self.session.hertz_fit_widget:
            self.session.hertz_fit_widget.update()
