"""This will be a collection of legends to be used with charts.
"""


import string
from reportlab.graphics.shapes import *
from reportlab.graphics.widgetbase import Widget
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.charts.barchart1 import sample2


# This one was originally written by Aaron (for Pingo, I think).

class Swatches0(Widget):
    """A very simple legend containing rectangular swatches and strings.

    Strings can be nicely aligned left or right to the swatches.
    """
    
    _attrmap = {
        "x": isNumber,
        "y": isNumber,
        "deltax": isNumber,
        "deltay": isNumber,
        "dxTextSpace": isNumber,
        "dx": isNumber,
        "dy": isNumber,
        "columnMaximum": isNumber,
        "alignment": OneOf(("left", "right")), # align text on the left or right
        "colorNamePairs": None, # fix this
        }

    def __init__(self):
        # Upper-left reference point.
        self.x = 0
        self.y = 0
        # Alginment of text with respect to swatches.
        self.alignment = "left"
        # x- and y-distances between neighbouring swatches.
        self.deltax = 75
        self.deltay = 20
        # Size of swatch rectangle.
        self.dx = 10
        self.dy = 10
        # Distance between swatch rectangle and text.
        self.dxTextSpace = 10
        # Max. number of items per column.
        self.columnMaximum = 3
        # Color/name pairs.
        self.colorNamePairs = [ (colors.red, "red"),
                                (colors.blue, "blue"),
                                (colors.green, "green"),
                                (colors.pink, "pink"),
                                (colors.yellow, "yellow") ]


    def _calculateMaxWidth(self, colorNamePairs):
        "Calculate the maximum width of some given strings."

        texts = map(lambda p:p[1], colorNamePairs[:3])
        widths = []
        for i in range(len(texts)):
            texts[i] = String(0,0, str(texts[i]))
            ti = texts[i]
            widths.append(stringWidth(ti.text, ti.fontName, ti.fontSize))
        maxWidth = max(widths)

        return maxWidth


    def draw(self):
        g = Group()
        colorNamePairs = self.colorNamePairs
        thisx = upperleftx = self.x
        thisy = upperlefty = self.y - self.dx
        dx, dy = self.dx, self.dy

        columnCount = 0
        count = 0
        for col, name in colorNamePairs:
            if self.alignment == "left":
                # align text to left
                t = String(thisx, thisy, str(name))
                j = columnCount*self.columnMaximum
                d = self._calculateMaxWidth(colorNamePairs[j:])
                t.x = t.x + d
                t.textAnchor = "end"
                r = Rect(thisx+d+self.dxTextSpace,thisy, dx, dy)
            elif self.alignment == "right":
                # align text to right
                t = String(thisx+self.dx+self.dxTextSpace, thisy, str(name))
                t.textAnchor = "start"
                r = Rect(thisx,thisy, dx, dy)
            else:
                raise ValueError, "bad alignment"
            r.fillColor = col
            g.add(t)
            g.add(r)
            if count == self.columnMaximum-1:
                count = 0
                thisx = thisx+self.deltax
                thisy = upperlefty
                columnCount = columnCount + 1
            else:
                thisy = thisy-self.deltay
                count = count+1

        return g


    def demo(self):
        "Make sample swatches."

        d = Drawing(200, 100)
        
        swatches = Swatches0()
        swatches.alignment = 'left'
        swatches.x = 0
        swatches.y = 100
        swatches.dxTextSpace = 5
        items = string.split('red green blue yellow pink black white', ' ')
        items = map(lambda i:(getattr(colors, i), i), items)
        swatches.colorNamePairs = items

        d.add(swatches, 'legend')

        return d


def sample1c():
    "Make sample swatches."
    
    d = Drawing(200, 100)
    
    swatches = Swatches0()
    swatches.alignment = 'right'
    swatches.x = 0
    swatches.y = 100
    swatches.dxTextSpace = 5
    items = string.split('red green blue yellow pink black white', ' ')
    items = map(lambda i:(getattr(colors, i), i), items)
    swatches.colorNamePairs = items

    d.add(swatches, 'legend')

    return d


def sample2c():
    "Make sample swatches."

    d = Drawing(200, 100)
    
    swatches = Swatches0()
    swatches.alignment = 'right'
    swatches.x = 20
    swatches.y = 90
    swatches.deltax = 60
    swatches.dxTextSpace = 10
    swatches.columnMaximum = 4
    items = string.split('red green blue yellow pink black white', ' ')
    items = map(lambda i:(getattr(colors, i), i), items)
    swatches.colorNamePairs = items

    d.add(swatches, 'legend')

    return d


def sample3c():
    "Make sample swatches."

    d = sample2()
    
    swatches = Swatches0()
    swatches.alignment = 'right'
    swatches.x = 80
    swatches.y = 190
    swatches.deltax = 60
    swatches.dxTextSpace = 10
    swatches.columnMaximum = 4
    items = [(colors.red, 'before'), (colors.green, 'after')]
    swatches.colorNamePairs = items

    d.add(swatches, 'legend')

    return d