#copyright ReportLab Inc. 2001
#see license.txt for license details
#history www.reportlab.co.uk/rl-cgi/viewcvs.cgi/rlextra/graphics/Csrc/renderPM/renderP.py
#$Header: /tmp/reportlab/reportlab/graphics/renderPM.py,v 1.28 2003/04/17 11:28:28 rgbecker Exp $
__version__=''' $Id: renderPM.py,v 1.28 2003/04/17 11:28:28 rgbecker Exp $ '''
"""Usage:
    from reportlab.graphics import renderPM
    renderPM.drawToFile(drawing,filename,fmt='GIF',configPIL={....})
Other functions let you create a PM drawing as string or into a PM buffer.
Execute the script to see some test drawings."""

from reportlab.graphics.shapes import *
from reportlab.graphics.renderbase import StateTracker, getStateDelta
from reportlab.pdfbase.pdfmetrics import getFont
from reportlab.lib.logger import warnOnce
from math import sin, cos, pi, ceil
from reportlab.lib.utils import getStringIO
from reportlab import rl_config

class RenderPMError(Exception):
    pass

import string, os, sys

try:
    import _renderPM
except ImportError, errMsg:
    raise ImportError, "No module named _renderPM\n" + \
        (str(errMsg)!='No module named _renderPM' and "it may be the wrong version or badly installed!" or
                                    "see http://www.reportlab.com/rl_addons.html")

from types import TupleType, ListType
_SeqTypes = (TupleType,ListType)

def _getImage():
    try:
        from PIL import Image
    except ImportError:
        import Image
    return Image

def Color2Hex(c):
    #assert isinstance(colorobj, colors.Color) #these checks don't work well RGB
    if c: return ((0xFF&int(255*c.red)) << 16) | ((0xFF&int(255*c.green)) << 8) | (0xFF&int(255*c.blue))
    return c

# the main entry point for users...
def draw(drawing, canvas, x, y, showBoundary=rl_config.showBoundary):
    """As it says"""
    R = _PMRenderer()
    R.draw(drawing, canvas, x, y)

from reportlab.graphics.renderbase import Renderer
class _PMRenderer(Renderer):
    """This draws onto a pix map image. It needs to be a class
    rather than a function, as some image-specific state tracking is
    needed outside of the state info in the SVG model."""

    def __init__(self):
        self._tracker = StateTracker()

    def pop(self):
        self._tracker.pop()
        self.applyState()

    def push(self,node):
        deltas = getStateDelta(node)
        self._tracker.push(deltas)
        self.applyState()

    def applyState(self):
        s = self._tracker.getState()
        self._canvas.ctm = s['ctm']
        self._canvas.strokeWidth = s['strokeWidth']
        self._canvas.strokeColor = Color2Hex(s['strokeColor'])
        self._canvas.lineCap = s['strokeLineCap']
        self._canvas.lineJoin = s['strokeLineJoin']
        da = s['strokeDashArray']
        da = da and (0,da) or None
        self._canvas.dashArray = da
        self._canvas.fillColor = Color2Hex(s['fillColor'])
        self._canvas.setFont(s['fontName'], s['fontSize'])

    def draw(self, drawing, canvas, x=0, y=0, showBoundary=rl_config.showBoundary):
        """This is the top level function, which
        draws the drawing at the given location.
        The recursive part is handled by drawNode."""
        #stash references for ease of  communication
        self._canvas = canvas
        canvas.__dict__['_drawing'] = self._drawing = drawing
        try:
            if showBoundary: canvas.rect(x, y, drawing.width, drawing.height)
            canvas.saveState()
            deltas = STATE_DEFAULTS.copy()
            deltas['transform'] = [1,0,0,1,x,y]
            self._tracker.push(deltas)
            self.applyState()
            self.drawNode(drawing)
            self.pop()
            canvas.restoreState()
        finally:
            #remove any circular references
            del self._canvas, self._drawing, canvas._drawing

    def drawNode(self, node):
        """This is the recursive method called for each node
        in the tree"""

        #apply state changes
        self.push(node)

        #draw the object, or recurse
        self.drawNodeDispatcher(node)

        # restore the state
        self.pop()

    def drawRect(self, rect):
        c = self._canvas
        if rect.rx == rect.ry == 0:
            #plain old rectangle, draw clockwise (x-axis to y-axis) direction
            c.pathBegin()
            c.moveTo(rect.x, rect.y)
            c.lineTo(rect.x+rect.width, rect.y)
            c.lineTo(rect.x+rect.width, rect.y + rect.height)
            c.lineTo(rect.x, rect.y + rect.height)
            c.pathClose()
        else:
            c.roundRect(rect.x,rect.y, rect.width, rect.height, rect.rx, rect.ry)
        c.fillstrokepath()

    def drawLine(self, line):
        c = self._canvas
        if c.strokeColor is not None:
            c = self._canvas
            c.pathBegin()
            c.moveTo(line.x1,line.y1)
            c.lineTo(line.x2,line.y2)
            c.pathStroke()

    def drawImage(self, image):
        if image.path and os.path.exists(image.path):
            if type(image.path) is type(''):
                im = _getImage().open(image.path).convert('RGB')
            else:
                im = image.path.convert('RGB')
            srcW, srcH = im.size
            dstW, dstH = image.width, image.height
            if dstW is None: dstW = srcW
            if dstH is None: dstH = srcH
            self._canvas._aapixbuf(
                    image.x, image.y, dstW, dstH,
                    im.tostring(), srcW, srcH, 3,
                    )

    def drawCircle(self, circle):
        c = self._canvas
        c.circle(circle.cx,circle.cy, circle.r)
        c.fillstrokepath()

    def drawPolyLine(self, polyline, _doClose=0):
        P = polyline.points
        assert len(P) >= 2, 'Polyline must have 1 or more points'
        c = self._canvas
        c.pathBegin()
        c.moveTo(P[0], P[1])
        for i in range(2, len(P), 2):
            c.lineTo(P[i], P[i+1])
        if _doClose:
            c.pathClose()
            c.pathFill()
        c.pathStroke()

    def drawEllipse(self, ellipse):
        c=self._canvas
        c.ellipse(ellipse.cx, ellipse.cy, ellipse.rx,ellipse.ry)
        c.fillstrokepath()

    def drawPolygon(self, polygon):
        self.drawPolyLine(polygon,_doClose=1)

    def drawString(self, stringObj):
        fill = self._canvas.fillColor
        if fill is not None:
            S = self._tracker.getState()
            text_anchor, x, y, text = S['textAnchor'], stringObj.x,stringObj.y,stringObj.text
            if not text_anchor in ['start','inherited']:
                font, font_size = S['fontName'], S['fontSize']
                textLen = stringWidth(text, font,font_size)
                if text_anchor=='end':
                    x = x-textLen
                elif text_anchor=='middle':
                    x = x - textLen/2
                else:
                    raise ValueError, 'bad value for textAnchor '+str(text_anchor)
            self._canvas.drawString(x,y,text)

    def drawPath(self, path):
        c = self._canvas
        if path is EmptyClipPath:
            del c._clipPaths[-1]
            if c._clipPaths:
                P = c._clipPaths[-1]
                icp = P.isClipPath
                P.isClipPath = 1
                self.drawPath(P)
                P.isClipPath = icp
            else:
                c.clipPathClear()
            return
        c.pathBegin()
        drawFuncs = (c.moveTo, c.lineTo, c.curveTo, c.pathClose)
        from reportlab.graphics.shapes import _renderPath
        isClosed = _renderPath(path, drawFuncs)
        if path.isClipPath:
            c.clipPathSet()
            c._clipPaths.append(path)
        else:
            if isClosed: c.pathFill()
            c.pathStroke()

def _setFont(gs,fontName,fontSize):
    try:
        gs.setFont(fontName,fontSize)
    except _renderPM.Error, errMsg:
        if errMsg.args[0]!="Can't find font!": raise
        #here's where we try to add a font to the canvas
        try:
            f = getFont(fontName)
            _renderPM.makeT1Font(fontName,f.face.findT1File(),f.encoding.vector)
        except:
            s1, s2 = map(str,sys.exc_info()[:2])
            raise RenderPMError, "Can't setFont(%s) missing the T1 files?\nOriginally %s: %s" % (fontName,s1,s2)
        gs.setFont(fontName,fontSize)

def _convert2pilp(im):
    Image = _getImage()
    return im.convert("P", dither=Image.NONE, palette=Image.ADAPTIVE)

def _saveAsPICT(im,fn,fmt):
    im = _convert2pilp(im)
    cols, rows = im.size
    s = _renderPM.pil2pict(cols,rows,im.tostring(),im.im.getpalette())
    if not hasattr(fn,'write'):
        open(os.path.splitext(fn)[0]+'.'+string.lower(fmt),'wb').write(s)
        from reportlab.lib.utils import markfilename
        markfilename(fn,creatorcode='ogle',filetype='PICT')
    else:
        fn.write(s)

BEZIER_ARC_MAGIC = 0.5522847498     #constant for drawing circular arcs w/ Beziers
class PMCanvas:
    def __init__(self,w,h,dpi=72,bg=0xffffff,configPIL=None):
        '''configPIL dict is passed to image save method'''
        scale = dpi/72.0
        self.__dict__['_gs'] = _renderPM.gstate(w,h,bg=bg)
        self.__dict__['_bg'] = bg
        self.__dict__['_baseCTM'] = (scale,0,0,scale,0,0)
        self.__dict__['_clipPaths'] = []
        self.__dict__['configPIL'] = configPIL
        self.ctm = self._baseCTM

    def _drawTimeResize(self,w,h,bg=None):
        if bg is None: bg = self._bg
        self._drawing.width, self._drawing.height = w, h
        A = {'ctm':None, 'strokeWidth':None, 'strokeColor':None, 'lineCap':None, 'lineJoin':None, 'dashArray':None, 'fillColor':None}
        gs = self._gs
        fN,fS = gs.fontName, gs.fontSize
        for k in A.keys():
            A[k] = getattr(gs,k)
        del gs, self._gs
        gs = self.__dict__['_gs'] = _renderPM.gstate(w,h,bg=bg)
        for k in A.keys():
            setattr(self,k,A[k])
        gs.setFont(fN,fS)

    def toPIL(self):
        im = _getImage().new('RGB', size=(self._gs.width, self._gs.height))
        im.fromstring(self._gs.pixBuf)
        return im

    def saveToFile(self,fn,fmt=None):
        im = self.toPIL()
        if fmt is None:
            if type(fn) is not StringType:
                raise ValueError, "Invalid type '%s' for fn when fmt is None" % type(fn)
        else:
            fmt = string.upper(fmt)
            if fmt in ['GIF']:
                im = _convert2pilp(im)
            elif fmt in ['PCT','PICT']:
                return _saveAsPICT(im,fn,fmt)
            elif fmt in ['PNG','TIFF','BMP', 'PPM', 'TIF']:
                if fmt=='TIF': fmt = 'TIFF'
                if fmt=='PNG':
                    try:
                        from PIL import PngImagePlugin
                    except ImportError:
                        import PngImagePlugin
            elif fmt in ('JPG','JPEG'):
                fmt = 'JPEG'
            else:
                raise RenderPMError,"Unknown image kind %s" % fmt
            apply(im.save,(fn,fmt),self.configPIL or {})
            if not hasattr(fn,'write'):
                from reportlab.lib.utils import markfilename
                markfilename(fn,creatorcode='ogle',filetype='PICT')

    def saveToString(self,fmt='GIF'):
        s = getStringIO()
        self.saveToFile(s,fmt=fmt)
        return s.getvalue()

    def _saveToBMP(self,f):
        '''
        Niki Spahiev, <niki@vintech.bg>, asserts that this is a respectable way to get BMP without PIL
        f is a file like object to which the BMP is written
        '''
        import struct
        gs = self._gs
        pix, width, height = gs.pixBuf, gs.width, gs.height
        f.write(struct.pack('=2sLLLLLLhh24x','BM',len(pix)+54,0,54,40,width,height,1,24))
        rowb = width * 3
        for o in range(len(pix),0,-rowb):
            f.write(pix[o-rowb:o])
        f.write( '\0' * 14 )

    def setFont(self,fontName,fontSize):
        _setFont(self._gs,fontName,fontSize)

    def __setattr__(self,name,value):
        setattr(self._gs,name,value)

    def __getattr__(self,name):
        return getattr(self._gs,name)

    def fillstrokepath(self):
        self.pathFill()
        self.pathStroke()

    def _bezierArcSegmentCCW(self, cx,cy, rx,ry, theta0, theta1):
        """compute the control points for a bezier arc with theta1-theta0 <= 90.
        Points are computed for an arc with angle theta increasing in the
        counter-clockwise (CCW) direction.  returns a tuple with starting point
        and 3 control points of a cubic bezier curve for the curvto opertator"""

        # Requires theta1 - theta0 <= 90 for a good approximation
        assert abs(theta1 - theta0) <= 90
        cos0 = cos(pi*theta0/180.0)
        sin0 = sin(pi*theta0/180.0)
        x0 = cx + rx*cos0
        y0 = cy + ry*sin0

        cos1 = cos(pi*theta1/180.0)
        sin1 = sin(pi*theta1/180.0)

        x3 = cx + rx*cos1
        y3 = cy + ry*sin1

        dx1 = -rx * sin0
        dy1 = ry * cos0

        #from pdfgeom
        halfAng = pi*(theta1-theta0)/(2.0 * 180.0)
        k = abs(4.0 / 3.0 * (1.0 - cos(halfAng) ) /(sin(halfAng)) )
        x1 = x0 + dx1 * k
        y1 = y0 + dy1 * k

        dx2 = -rx * sin1
        dy2 = ry * cos1

        x2 = x3 - dx2 * k
        y2 = y3 - dy2 * k
        return ((x0,y0), ((x1,y1), (x2,y2), (x3,y3)) )

    def bezierArcCCW(self, cx,cy, rx,ry, theta0, theta1):
        """return a set of control points for Bezier approximation to an arc
        with angle increasing counter clockwise. No requirement on |theta1-theta0| <= 90
        However, it must be true that theta1-theta0 > 0."""

        # I believe this is also clockwise
        # pretty much just like Robert Kern's pdfgeom.BezierArc
        angularExtent = theta1 - theta0
        # break down the arc into fragments of <=90 degrees
        if abs(angularExtent) <= 90.0:  # we just need one fragment
            angleList = [(theta0,theta1)]
        else:
            Nfrag = int( ceil( abs(angularExtent)/90.) )
            fragAngle = float(angularExtent)/ Nfrag  # this could be negative
            angleList = []
            for ii in range(Nfrag):
                a = theta0 + ii * fragAngle
                b = a + fragAngle # hmm.. is I wonder if this is precise enought
                angleList.append((a,b))

        ctrlpts = []
        for (a,b) in angleList:
            if not ctrlpts: # first time
                [(x0,y0), pts] = self._bezierArcSegmentCCW(cx,cy, rx,ry, a,b)
                ctrlpts.append(pts)
            else:
                [(tmpx,tmpy), pts] = self._bezierArcSegmentCCW(cx,cy, rx,ry, a,b)
                ctrlpts.append(pts)
        return ((x0,y0), ctrlpts)

    def addEllipsoidalArc(self, cx,cy, rx, ry, ang1, ang2):
        """adds an ellisesoidal arc segment to a path, with an ellipse centered
        on cx,cy and with radii (major & minor axes) rx and ry.  The arc is
        drawn in the CCW direction.  Requires: (ang2-ang1) > 0"""

        ((x0,y0), ctrlpts) = self.bezierArcCCW(cx,cy, rx,ry,ang1,ang2)

        self.lineTo(x0,y0)
        for ((x1,y1), (x2,y2),(x3,y3)) in ctrlpts:
            self.curveTo(x1,y1,x2,y2,x3,y3)

    def roundRect(self, x, y, width, height, rx,ry):
        """rect(self, x, y, width, height, rx,ry):
        Draw a rectangle if rx or rx and ry are specified the corners are
        rounded with ellipsoidal arcs determined by rx and ry
        (drawn in the counter-clockwise direction)"""
        if rx==0: rx = ry
        if ry==0: ry = rx
        x2 = x + width
        y2 = y + height
        self.pathBegin()
        self.moveTo(x+rx,y)
        self.addEllipsoidalArc(x2-rx, y+ry, rx, ry, 270, 360 )
        self.addEllipsoidalArc(x2-rx, y2-ry, rx, ry, 0, 90)
        self.addEllipsoidalArc(x+rx, y2-ry, rx, ry, 90, 180)
        self.addEllipsoidalArc(x+rx, y+ry, rx, ry, 180,  270)
        self.pathClose()

    def circle(self, cx, cy, r):
        "add closed path circle with center cx,cy and axes r: counter-clockwise orientation"
        self.ellipse(cx,cy,r,r)

    def ellipse(self, cx,cy,rx,ry):
        """add closed path ellipse with center cx,cy and axes rx,ry: counter-clockwise orientation
        (remember y-axis increases downward) """
        self.pathBegin()
        # first segment
        x0 = cx + rx   # (x0,y0) start pt
        y0 = cy

        x3 = cx        # (x3,y3) end pt of arc
        y3 = cy-ry

        x1 = cx+rx
        y1 = cy-ry*BEZIER_ARC_MAGIC

        x2 = x3 + rx*BEZIER_ARC_MAGIC
        y2 = y3
        self.moveTo(x0, y0)
        self.curveTo(x1,y1,x2,y2,x3,y3)
        # next segment
        x0 = x3
        y0 = y3

        x3 = cx-rx
        y3 = cy

        x1 = cx-rx*BEZIER_ARC_MAGIC
        y1 = cy-ry

        x2 = x3
        y2 = cy- ry*BEZIER_ARC_MAGIC
        self.curveTo(x1,y1,x2,y2,x3,y3)
        # next segment
        x0 = x3
        y0 = y3

        x3 = cx
        y3 = cy+ry

        x1 = cx-rx
        y1 = cy+ry*BEZIER_ARC_MAGIC

        x2 = cx -rx*BEZIER_ARC_MAGIC
        y2 = cy+ry
        self.curveTo(x1,y1,x2,y2,x3,y3)
        #last segment
        x0 = x3
        y0 = y3

        x3 = cx+rx
        y3 = cy

        x1 = cx+rx*BEZIER_ARC_MAGIC
        y1 = cy+ry

        x2 = cx+rx
        y2 = cy+ry*BEZIER_ARC_MAGIC
        self.curveTo(x1,y1,x2,y2,x3,y3)
        self.pathClose()

    def saveState(self):
        '''do nothing for compatibility'''
        pass

    restoreState = saveState

def drawToPMCanvas(d, dpi=72, bg=0xfffffff, configPIL=None, showBoundary=rl_config.showBoundary):
    w = int(d.width+0.5)
    h = int(d.height+0.5)
    c = PMCanvas(w, h, dpi=dpi, bg=bg, configPIL=configPIL)
    draw(d, c, 0, 0)
    return c

def drawToPIL(d, dpi=72, bg=0xfffffff, configPIL=None, showBoundary=rl_config.showBoundary):
    return drawToPMCanvas(d, dpi=dpi, bg=bg, configPIL=configPIL, showBoundary=showBoundary).toPIL()

def drawToPILP(d, dpi=72, bg=0xfffffff, configPIL=None, showBoundary=rl_config.showBoundary):
    Image = _getImage()
    im = drawToPIL(d, dpi=dpi, bg=bg, configPIL=configPIL, showBoundary=showBoundary)
    return im.convert("P", dither=Image.NONE, palette=Image.ADAPTIVE)

def drawToFile(d,fn,fmt='GIF', dpi=72, bg=0xfffffff, configPIL=None, showBoundary=rl_config.showBoundary):
    '''create a pixmap and draw drawing, d to it then save as a file
    configPIL dict is passed to image save method'''
    c = drawToPMCanvas(d, dpi=dpi, bg=bg, configPIL=configPIL, showBoundary=showBoundary)
    c.saveToFile(fn,fmt)

def drawToString(d,fmt='GIF', dpi=72, bg=0xfffffff, configPIL=None, showBoundary=rl_config.showBoundary):
    s = getStringIO()
    drawToFile(d,s,fmt=fmt, dpi=dpi, bg=bg, configPIL=configPIL)
    return s.getvalue()

save = drawToFile

if __name__=='__main__':
    def ext(x):
        if x=='tiff': x='tif'
        return x

    def test():
        #grab all drawings from the test module and write out.
        #make a page of links in HTML to assist viewing.
        import os
        from reportlab.graphics.testshapes import getAllTestDrawings
        drawings = []
        if not os.path.isdir('pmout'):
            os.mkdir('pmout')
        htmlTop = """<html><head><title>renderGD output results</title></head>
        <body>
        <h1>renderPM results of output</h1>
        """
        htmlBottom = """</body>
        </html>
        """
        html = [htmlTop]

        i = 0
        #print in a loop, with their doc strings
        for (drawing, docstring, name) in getAllTestDrawings():
            if 1 or i==10:
                w = int(drawing.width)
                h = int(drawing.height)
                html.append('<hr><h2>Drawing %s %d</h2>\n<pre>%s</pre>' % (name, i, docstring))

                for k in ['gif','tiff', 'png', 'jpg', 'pct']:
                    if k in ['gif','png','jpg','pct']:
                        html.append('<p>%s format</p>\n' % string.upper(k))
                    try:
                        filename = 'renderPM%d.%s' % (i, ext(k))
                        fullpath = os.path.join('pmout', filename)
                        if os.path.isfile(fullpath):
                            os.remove(fullpath)
                        drawToFile(drawing,fullpath,fmt=k)
                        if k in ['gif','png','jpg','pct']:
                            html.append('<img src="%s" border="1"><br>\n' % filename)
                        print 'wrote',fullpath
                    except AttributeError:
                        print 'Problem drawing %s file'%k
                        raise
            i = i + 1
            #if i==10: break
        html.append(htmlBottom)
        htmlFileName = os.path.join('pmout', 'index.html')
        open(htmlFileName, 'w').writelines(html)
        print 'wrote %s' % htmlFileName
    test()
