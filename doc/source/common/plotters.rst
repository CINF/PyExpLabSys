.. _common-doc-plotters:

************************************
The plotters module plotter backends
************************************

The plotters module contains classes for easy plotting of data.

The data logger
===============

The :class:`.DataLogger` is a general purpose plotter that is suitable
for plotting data sets as they are being gathered. The data logger
uses the qwt backend, though the class :class:`.QwtPlot`, that forms
the plot by means of the PyQwt library.

Usage Example
-------------

.. code-block:: python

    import sys
    import time
    import random
    import numpy as np
    from PyQt4 import Qt, QtGui, QtCore
    from PyExpLabSys.common.plotters import DataPlotter
    
    class TestApp(QtGui.QWidget):
        """Test Qt application"""
    
        def __init__(self):
            super(TestApp, self).__init__()
            # Form plotnames
            self.plots_l = ['signal1', 'signal2']
            self.plots_r = ['aux_signal1']
            
            self.plotter = DataPlotter(
                self.plots_l, right_plotlist=self.plots_r, parent=self,
                left_log=True, title='Awesome plots',
                yaxis_left_label='Log sine, cos', yaxis_right_label='Noisy line',
                xaxis_label='Time since start [s]',
                legend='right', left_thickness=[2, 8], right_thickness=6,
                left_colors=['firebrick', 'darkolivegreen'],
                right_colors=['darksalmon'])
    
            hbox = QtGui.QHBoxLayout()
            hbox.addWidget(self.plotter.plot)
            self.setLayout(hbox)
            self.setGeometry(5, 5, 500, 500)
    
            self.start = time.time()
            QtCore.QTimer.singleShot(10, self.main)
    
        def main(self):
            """Simulate gathering one set of points and adding them to plot"""
            elapsed = time.time() - self.start
            value = (np.sin(elapsed) + 1.1) * 1E-9
            self.plotter.add_point('signal1', (elapsed, value))
            value = (np.cos(elapsed) + 1.1) * 1E-8
            self.plotter.add_point('signal2', (elapsed, value))
            value = elapsed + random.random()
            self.plotter.add_point('aux_signal1', (elapsed, value))
    
            QtCore.QTimer.singleShot(100, self.main)
    
    def main():
        """Main method"""
        app = Qt.QApplication(sys.argv)
        testapp = TestApp()
        testapp.show()
        sys.exit(app.exec_())
    
    if __name__ == '__main__':
        main()

plotters module
---------------

.. automodule:: PyExpLabSys.common.plotters
   :members:
   :member-order: bysource
   :show-inheritance:

The qwt backend
===============

plotters_backend_qwt
--------------------

.. automodule:: PyExpLabSys.common.plotters_backend_qwt
   :members:
   :member-order: bysource
   :show-inheritance:

.. _colors-section:

Colors
------

==================== ==================== ==================== ====================
aliceblue            antiquewhite         aqua                 aquamarine          
azure                beige                bisque               black               
blanchedalmond       blue                 blueviolet           brown               
burlywood            cadetblue            chartreuse           chocolate           
coral                cornflowerblue       cornsilk             crimson             
cyan                 darkblue             darkcyan             darkgoldenrod       
darkgray             darkgreen            darkgrey             darkkhaki           
darkmagenta          darkolivegreen       darkorange           darkorchid          
darkred              darksalmon           darkseagreen         darkslateblue       
darkslategray        darkslategrey        darkturquoise        darkviolet          
deeppink             deepskyblue          dimgray              dimgrey             
dodgerblue           firebrick            floralwhite          forestgreen         
fuchsia              gainsboro            ghostwhite           gold                
goldenrod            gray                 green                greenyellow         
grey                 honeydew             hotpink              indianred           
indigo               ivory                khaki                lavender            
lavenderblush        lawngreen            lemonchiffon         lightblue           
lightcoral           lightcyan            lightgoldenrodyellow lightgray           
lightgreen           lightgrey            lightpink            lightsalmon         
lightseagreen        lightskyblue         lightslategray       lightslategrey      
lightsteelblue       lightyellow          lime                 limegreen           
linen                magenta              maroon               mediumaquamarine    
mediumblue           mediumorchid         mediumpurple         mediumseagreen      
mediumslateblue      mediumspringgreen    mediumturquoise      mediumvioletred     
midnightblue         mintcream            mistyrose            moccasin            
navajowhite          navy                 oldlace              olive               
olivedrab            orange               orangered            orchid              
palegoldenrod        palegreen            paleturquoise        palevioletred       
papayawhip           peachpuff            peru                 pink                
plum                 powderblue           purple               red                 
rosybrown            royalblue            saddlebrown          salmon              
sandybrown           seagreen             seashell             sienna              
silver               skyblue              slateblue            slategray           
slategrey            snow                 springgreen          steelblue           
tan                  teal                 thistle              tomato              
transparent          turquoise            violet               wheat               
white                whitesmoke           yellow               yellowgreen
==================== ==================== ==================== ====================
