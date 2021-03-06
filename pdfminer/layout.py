#!/usr/bin/env python2

import logging

from .utils import INF, Plane, get_bound, uniq, fsplit, isany, dist, bbox2str, matrix2str, apply_matrix_pt


class IndexAssigner(object):

    def __init__(self, index=0):
        self.index = index

    def run(self, obj):
        if isinstance(obj, LTTextBox):
            obj.index = self.index
            self.index += 1
        elif isinstance(obj, LTTextGroup):
            for x in obj:
                self.run(x)


class LAParams(object):

    def __init__(self, line_overlap=0.5, char_margin=2.0, line_margin=0.5, word_margin=0.1, boxes_flow=0.5,
                 detect_vertical=False, all_texts=False):
        self.line_overlap = line_overlap
        self.char_margin = char_margin
        self.line_margin = line_margin
        self.word_margin = word_margin
        self.boxes_flow = boxes_flow
        self.detect_vertical = detect_vertical
        self.all_texts = all_texts

    def __repr__(self):
        return ('<LAParams: char_margin=%.1f, line_margin=%.1f, word_margin=%.1f all_texts=%r>' %
                (self.char_margin, self.line_margin, self.word_margin, self.all_texts))


class LTItem(object):

    def analyze(self, laparams):
        """Perform the layout analysis."""
        return


class LTText(object):

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.get_text())

    def get_text(self):
        raise NotImplementedError


class LTComponent(LTItem):

    def __init__(self, bbox):
        LTItem.__init__(self)
        self.set_bbox(bbox)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, bbox2str(self.bbox))

    def set_bbox(self, xxx_todo_changeme):
        (x0, y0, x1, y1) = xxx_todo_changeme
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.width = x1 - x0
        self.height = y1 - y0
        self.bbox = (x0, y0, x1, y1)

    def is_empty(self):
        return self.width <= 0 or self.height <= 0

    def is_hoverlap(self, obj):
        assert isinstance(obj, LTComponent)
        return obj.x0 <= self.x1 and self.x0 <= obj.x1

    def hdistance(self, obj):
        assert isinstance(obj, LTComponent)
        if self.is_hoverlap(obj):
            return 0
        else:
            return min(abs(self.x0 - obj.x1), abs(self.x1 - obj.x0))

    def hoverlap(self, obj):
        assert isinstance(obj, LTComponent)
        if self.is_hoverlap(obj):
            return min(abs(self.x0 - obj.x1), abs(self.x1 - obj.x0))
        else:
            return 0

    def is_voverlap(self, obj):
        assert isinstance(obj, LTComponent)
        return obj.y0 <= self.y1 and self.y0 <= obj.y1

    def vdistance(self, obj):
        assert isinstance(obj, LTComponent)
        if self.is_voverlap(obj):
            return 0
        else:
            return min(abs(self.y0 - obj.y1), abs(self.y1 - obj.y0))

    def voverlap(self, obj):
        assert isinstance(obj, LTComponent)
        if self.is_voverlap(obj):
            return min(abs(self.y0 - obj.y1), abs(self.y1 - obj.y0))
        else:
            return 0


class LTCurve(LTComponent):

    def __init__(self, linewidth, pts):
        LTComponent.__init__(self, get_bound(pts))
        self.pts = pts
        self.linewidth = linewidth

    def get_pts(self):
        return ','.join('%.3f,%.3f' % p for p in self.pts)


class LTLine(LTCurve):

    def __init__(self, linewidth, p0, p1):
        LTCurve.__init__(self, linewidth, [p0, p1])


class LTRect(LTCurve):

    def __init__(self, linewidth, xxx_todo_changeme1):
        (x0, y0, x1, y1) = xxx_todo_changeme1
        LTCurve.__init__(self, linewidth, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


class LTImage(LTComponent):

    def __init__(self, name, stream, bbox):
        LTComponent.__init__(self, bbox)
        self.name = name
        self.stream = stream
        self.srcsize = (stream.get_any(('W', 'Width')), stream.get_any(('H', 'Height')))
        self.imagemask = stream.get_any(('IM', 'ImageMask'))
        self.bits = stream.get_any(('BPC', 'BitsPerComponent'), 1)
        self.colorspace = stream.get_any(('CS', 'ColorSpace'))
        if not isinstance(self.colorspace, list):
            self.colorspace = [self.colorspace]


    def __repr__(self):
        return '<%s(%s) %s %r>' % (self.__class__.__name__, self.name, bbox2str(self.bbox), self.srcsize)


class LTAnon(LTItem, LTText):

    def __init__(self, text):
        self._text = text

    def get_text(self):
        return self._text


class LTChar(LTComponent, LTText):

    def __init__(self, matrix, font, fontsize, scaling, rise, text, textwidth, textdisp):
        LTText.__init__(self)
        self._text = text
        self.matrix = matrix
        self.fontname = font.fontname
        self.adv = textwidth * fontsize * scaling
        # compute the boundary rectangle.
        if font.is_vertical():
            # vertical
            width = font.get_width() * fontsize
            (vx,vy) = textdisp
            if vx is None:
                vx = width / 2
            else:
                vx = vx * fontsize * .001
            vy = (1000 - vy) * fontsize * .001
            tx = -vx
            ty = vy + rise
            bll = (tx, ty + self.adv)
            bur = (tx + width, ty)
        else:
            # horizontal
            height = font.get_height() * fontsize
            descent = font.get_descent() * fontsize
            ty = descent + rise
            bll = (0, ty)
            bur = (self.adv, ty+height)
        (a, b, c, d, e, f) = self.matrix
        self.upright = (a*d*scaling > 0 >= b * c)
        (x0,y0) = apply_matrix_pt(self.matrix, bll)
        (x1,y1) = apply_matrix_pt(self.matrix, bur)
        if x1 < x0:
            (x0, x1) = (x1, x0)
        if y1 < y0:
            (y0, y1) = (y1, y0)
        LTComponent.__init__(self, (x0, y0, x1, y1))
        if font.is_vertical():
            self.size = self.width
        else:
            self.size = self.height

    def __repr__(self):
        return ('<%s %s matrix=%s font=%r adv=%s text=%r>' %
                (self.__class__.__name__, bbox2str(self.bbox),
                 matrix2str(self.matrix), self.fontname, self.adv,
                 self.get_text()))

    def get_text(self):
        return self._text

    def is_compatible(self, obj):
        """Returns True if two characters can coexist in the same line."""
        return True


class LTContainer(LTComponent):

    def __init__(self, bbox):
        LTComponent.__init__(self, bbox)
        self._objs = []

    def __iter__(self):
        return iter(self._objs)

    def __len__(self):
        return len(self._objs)

    def add(self, obj):
        self._objs.append(obj)

    def extend(self, objs):
        for obj in objs:
            self.add(obj)

    def analyze(self, laparams):
        for obj in self._objs:
            obj.analyze(laparams)


class LTExpandableContainer(LTContainer):

    def __init__(self):
        LTContainer.__init__(self, (+INF, +INF, -INF, -INF))

    def add(self, obj):
        LTContainer.add(self, obj)
        self.set_bbox((min(self.x0, obj.x0), min(self.y0, obj.y0), max(self.x1, obj.x1), max(self.y1, obj.y1)))


class LTTextContainer(LTExpandableContainer, LTText):

    def __init__(self):
        LTText.__init__(self)
        LTExpandableContainer.__init__(self)

    def get_text(self):
        return ''.join(obj.get_text() for obj in self if isinstance(obj, LTText))


class LTTextLine(LTTextContainer):

    def __init__(self, word_margin):
        LTTextContainer.__init__(self)
        self.word_margin = word_margin

    def __repr__(self):
        return '<%s %s %r>' % (self.__class__.__name__, bbox2str(self.bbox), self.get_text())

    def analyze(self, laparams):
        LTTextContainer.analyze(self, laparams)
        LTContainer.add(self, LTAnon('\n'))

    def find_neighbors(self, plane, ratio):
        raise NotImplementedError


class LTTextLineHorizontal(LTTextLine):

    def __init__(self, word_margin):
        LTTextLine.__init__(self, word_margin)
        self._x1 = +INF

    def add(self, obj):
        if isinstance(obj, LTChar) and self.word_margin:
            margin = self.word_margin * obj.width
            if self._x1 < obj.x0 - margin:
                LTContainer.add(self, LTAnon(' '))
        self._x1 = obj.x1
        LTTextLine.add(self, obj)

    def find_neighbors(self, plane, ratio):
        d = ratio * self.height
        objs = plane.find((self.x0, self.y0-d, self.x1, self.y1 + d))
        return [obj for obj in objs
                if (isinstance(obj, LTTextLineHorizontal) and abs(obj.height-self.height) < d and
                    (abs(obj.x0-self.x0) < d or abs(obj.x1-self.x1) < d))]


class LTTextLineVertical(LTTextLine):

    def __init__(self, word_margin):
        LTTextLine.__init__(self, word_margin)
        self._y0 = -INF

    def add(self, obj):
        if isinstance(obj, LTChar) and self.word_margin:
            margin = self.word_margin * obj.height
            if obj.y1 + margin < self._y0:
                LTContainer.add(self, LTAnon(' '))
        self._y0 = obj.y0
        LTTextLine.add(self, obj)
        
    def find_neighbors(self, plane, ratio):
        d = ratio*self.width
        objs = plane.find((self.x0-d, self.y0, self.x1+d, self.y1))
        return [obj for obj in objs
                if (isinstance(obj, LTTextLineVertical) and abs(obj.width-self.width) < d and
                    (abs(obj.y0-self.y0) < d or abs(obj.y1-self.y1) < d))]


class LTTextBox(LTTextContainer):
    """A set of text objects that are grouped within a certain rectangular area."""

    def __init__(self):
        LTTextContainer.__init__(self)
        self.index = -1

    def __repr__(self):
        return '<%s(%s) %s %r>' % (self.__class__.__name__, self.index, bbox2str(self.bbox), self.get_text())


class LTTextBoxHorizontal(LTTextBox):
    
    def analyze(self, laparams):
        LTTextBox.analyze(self, laparams)
        # Sorting the lines by y1 like this is not perfect
        # pdfminer3k by hsoft uses average y position, but that has issues too
        self._objs = sorted(self._objs, key=lambda obj: -obj.y1)

    def get_writing_mode(self):
        return 'lr-tb'


class LTTextBoxVertical(LTTextBox):

    def analyze(self, laparams):
        LTTextBox.analyze(self, laparams)
        self._objs = sorted(self._objs, key=lambda obj: -obj.x1)

    def get_writing_mode(self):
        return 'tb-rl'


class LTTextGroup(LTTextContainer):

    def __init__(self, objs):
        LTTextContainer.__init__(self)
        self.extend(objs)


class LTTextGroupLRTB(LTTextGroup):
    
    def analyze(self, laparams):
        LTTextGroup.analyze(self, laparams)
        # reorder the objects from top-left to bottom-right.
        self._objs = sorted(self._objs, key=lambda obj:
                           (1 - laparams.boxes_flow) * obj.x0 - (1 + laparams.boxes_flow) * (obj.y0 + obj.y1))


class LTTextGroupTBRL(LTTextGroup):
    
    def analyze(self, laparams):
        LTTextGroup.analyze(self, laparams)
        # reorder the objects from top-right to bottom-left.
        self._objs = sorted(self._objs, key=lambda obj:
                            -(1 + laparams.boxes_flow) * (obj.x0 + obj.x1) - (1 - laparams.boxes_flow) * obj.y1)


class LTLayoutContainer(LTContainer):

    def __init__(self, bbox):
        LTContainer.__init__(self, bbox)
        self.groups = None

    def get_textlines(self, laparams, objs):
        obj0 = None
        line = None
        for obj1 in objs:
            if obj0 is not None:
                k = 0
                if (obj0.is_compatible(obj1) and obj0.is_voverlap(obj1) and
                        min(obj0.height, obj1.height) * laparams.line_overlap < obj0.voverlap(obj1) and
                        obj0.hdistance(obj1) < max(obj0.width, obj1.width) * laparams.char_margin):
                    # obj0 and obj1 is horizontally aligned:
                    #
                    #   +------+ - - -
                    #   | obj0 | - - +------+   -
                    #   |      |     | obj1 |   | (line_overlap)
                    #   +------+ - - |      |   -
                    #          - - - +------+
                    #
                    #          |<--->|
                    #        (char_margin)
                    k |= 1
                if (laparams.detect_vertical and obj0.is_compatible(obj1) and obj0.is_hoverlap(obj1) and
                        min(obj0.width, obj1.width) * laparams.line_overlap < obj0.hoverlap(obj1) and
                        obj0.vdistance(obj1) < max(obj0.height, obj1.height) * laparams.char_margin):
                    # obj0 and obj1 is vertically aligned:
                    #
                    #   +------+
                    #   | obj0 |
                    #   |      |
                    #   +------+ - - -
                    #     |    |     | (char_margin)
                    #     +------+ - -
                    #     | obj1 |
                    #     |      |
                    #     +------+
                    #
                    #     |<-->|
                    #   (line_overlap)
                    k |= 2
                if ((k & 1 and isinstance(line, LTTextLineHorizontal)) or
                        (k & 2 and isinstance(line, LTTextLineVertical))):
                    line.add(obj1)
                elif line is not None:
                    yield line
                    line = None
                else:
                    if k == 2:
                        line = LTTextLineVertical(laparams.word_margin)
                        line.add(obj0)
                        line.add(obj1)
                    elif k == 1:
                        line = LTTextLineHorizontal(laparams.word_margin)
                        line.add(obj0)
                        line.add(obj1)
                    else:
                        line = LTTextLineHorizontal(laparams.word_margin)
                        line.add(obj0)
                        yield line
                        line = None
            obj0 = obj1
        if line is None:
            line = LTTextLineHorizontal(laparams.word_margin)
            line.add(obj0)
        yield line

    def get_textboxes(self, laparams, lines):
        plane = Plane(lines)
        boxes = {}
        for line in lines:
            neighbors = line.find_neighbors(plane, laparams.line_margin)
            assert line in neighbors, line
            members = []
            for obj1 in neighbors:
                members.append(obj1)
                if obj1 in boxes:
                    members.extend(boxes.pop(obj1))
            if isinstance(line, LTTextLineHorizontal):
                box = LTTextBoxHorizontal()
            else:
                box = LTTextBoxVertical()
            for obj in uniq(members):
                box.add(obj)
                boxes[obj] = box
        done = set()
        for line in lines:
            box = boxes[line]
            if box in done:
                continue
            done.add(box)
            yield box

    def group_textboxes(self, laparams, boxes):
        if len(boxes) > 100:
            # Grouping this many boxes would take too long and it doesn't make much sense to do so
            # considering the type of grouping (nesting 2-sized subgroups) that is done here.
            logging.info("Too many boxes (%d) to group, skipping.", len(boxes))
            return boxes
        dists = []
        for obj1, obj2 in zip(boxes[0:], boxes[1:]):
            dists.append((0, dist(obj1, obj2), obj1, obj2))
        dists.sort()
        plane = Plane(boxes)
        while dists:
            (c, d, obj1, obj2) = dists.pop(0)
            if c == 0 and isany(obj1, obj2, plane):
                dists.append((1, d, obj1, obj2))
                continue
            if (isinstance(obj1, (LTTextBoxVertical, LTTextGroupTBRL)) or
                    isinstance(obj2, (LTTextBoxVertical, LTTextGroupTBRL))):
                group = LTTextGroupTBRL([obj1, obj2])
            else:
                group = LTTextGroupLRTB([obj1, obj2])
            plane.remove(obj1)
            plane.remove(obj2)
            dists = [n for n in dists if not n[2] in (obj1, obj2) and not n[3] in (obj1, obj2)]
            for other in plane:
                dists.append((0, dist(group, other), group, other))
            dists.sort()
            plane.add(group)
        assert len(plane) == 1
        return list(plane)
    
    def analyze(self, laparams):
        # textobjs is a list of LTChar objects, i.e.
        # it has all the individual characters in the page.
        (textobjs, otherobjs) = fsplit(lambda obj: isinstance(obj, LTChar), self._objs)
        for obj in otherobjs:
            obj.analyze(laparams)
        if not textobjs:
            return None
        textlines = list(self.get_textlines(laparams, textobjs))
        assert len(textobjs) <= sum(len(line._objs) for line in textlines)
        (empties, textlines) = fsplit(lambda obj: obj.is_empty(), textlines)
        for obj in empties:
            obj.analyze(laparams)
        textboxes = list(self.get_textboxes(laparams, textlines))
        assert len(textlines) == sum(len(box._objs) for box in textboxes)
        self.groups = self.group_textboxes(laparams, textboxes)
        assigner = IndexAssigner()
        for group in self.groups:
            group.analyze(laparams)
            assigner.run(group)
        textboxes.sort(key=lambda box: box.index)
        self._objs = textboxes + otherobjs + empties


class LTFigure(LTLayoutContainer):

    def __init__(self, name, bbox, matrix):
        self.name = name
        self.matrix = matrix
        (x, y, w, h) = bbox
        bbox = get_bound(apply_matrix_pt(matrix, (p, q)) for (p, q) in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)))
        LTLayoutContainer.__init__(self, bbox)

    def __repr__(self):
        return ('<%s(%s) %s matrix=%s>' %
                (self.__class__.__name__, self.name, bbox2str(self.bbox), matrix2str(self.matrix)))

    def analyze(self, laparams):
        if not laparams.all_texts:
            return
        LTLayoutContainer.analyze(self, laparams)


class LTPage(LTLayoutContainer):

    def __init__(self, pageid, bbox, rotate=0):
        LTLayoutContainer.__init__(self, bbox)
        self.pageid = pageid
        self.rotate = rotate

    def __repr__(self):
        return ('<%s(%r) %s rotate=%r>' %
                (self.__class__.__name__, self.pageid, bbox2str(self.bbox), self.rotate))
