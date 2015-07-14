# Author: Sergey Vartanov (me@enzet.ru)

# Convert SVG station layout to Shape file format.

import copy
import re
import sys
from xml.dom import minidom

sys.path.append('lib')

import path
import svg
from vector import Vector, Matrix3

usage = 'python ' + sys.argv[0] + ' <input SVG file> <output shape file>'
debug_svg_file_name = 'debug.svg'

if len(sys.argv) < 3:
    print 'Usage:', usage
    sys.exit(1)

input_file_name = sys.argv[1]
output_file_name = sys.argv[2]

input_map = open(input_file_name)

document = minidom.parse(input_map)
inner_svg = document.documentElement

def repr(element):
    s = str(element) + ' -'
    # if element.attributes:
    #     print element.attributes.items()
    #     for attribute in element.attributes.items():
    #         s += ' (' + str(attribute) + ')'
    return s


def extract_path(element, matrix):
    """
    Extract path from SVG <path> element.
    """
    current_path = element.attributes['d'].value
    p = path.Path()
    p.parse_from_svg(current_path)
    p.transform(matrix)
    return p


def get_bounds(paths):

    def get_for(get_component):
        min_c, p_min = 1000, None
        max_c, p_max = -1000, None
        for p in paths:
            for s in p.segments:
                if get_component(s.start) < min_c: 
                    min_c, p_min = get_component(s.start), p
                if get_component(s.start) > max_c: 
                    max_c, p_max = get_component(s.start), p
                if get_component(s.end) < min_c: 
                    min_c, p_min = get_component(s.end), p
                if get_component(s.end) > max_c: 
                    max_c, p_max = get_component(s.end), p
        return min_c, max_c, p_min, p_max

    min_x, max_x, p_min, p_max = get_for(lambda a: a.x)
    if p_min == p_max:
        min_y, max_y, p_min, p_max = get_for(lambda a: a.y)

    return p_min, p_max


def process(root, level, matrix):
    """
    Process SVG element.
    """
    if isinstance(root, minidom.Text):
        return
    # print (' ' * (level * 2)) + repr(root.localName)

    # Transformation

    if 'transform' in root.attributes.keys():
        new_matrix = None
        m = re.match('^translate\((?P<x>[0-9.-]*),(?P<y>[0-9.-]*)\)$', \
            root.attributes['transform'].value)
        if m:
            new_matrix = Matrix3([[1, 0, float(m.group('x'))],
                                  [0, 1, float(m.group('y'))],
                                  [0, 0, 1]])
        m = re.match('^matrix\((?P<a>[0-9.-]*),(?P<b>[0-9.-]*),' + \
                     '(?P<c>[0-9.-]*),(?P<d>[0-9.-]*),(?P<e>[0-9.-]*),' + \
                     '(?P<f>[0-9.-]*)\)$', root.attributes['transform'].value)
        if m:
            new_matrix = Matrix3([[float(m.group('a')), float(m.group('c')), float(m.group('e'))],
                                  [float(m.group('b')), float(m.group('d')), float(m.group('f'))],
                                  [0, 0, 1]])
        if new_matrix:
            matrix = copy.deepcopy(matrix) * new_matrix

    str_matrix = None
    if matrix:
        str_matrix = 'matrix(' + str(matrix.matrix[0][0]) + ',' + \
                                 str(matrix.matrix[1][0]) + ',' + \
                                 str(matrix.matrix[0][1]) + ',' + \
                                 str(matrix.matrix[1][1]) + ',' + \
                                 str(matrix.matrix[0][2]) + ',' + \
                                 str(matrix.matrix[1][2]) + ')'

    # Element detection

    if root.localName == 'g':
        a = 0
        for child in root.childNodes:
            if child.localName == 'path':
                a += 1
        if a == 10 or a == 3:
            print 'stairs'
            paths = []
            for child in root.childNodes:
                if child.localName == 'path':
                    paths.append(extract_path(child, matrix))
            p_min, p_max = get_bounds(paths)
            output.path(p_min.to_svg(), color='000000')
            output.path(p_max.to_svg(), color='000000')
        else:
            for child in root.childNodes:
                process(child, level + 1, matrix)
    elif root.localName == 'path':
        p = extract_path(root, matrix)
        output.path(p.to_svg(), color='FF0000')
    else:
        for child in root.childNodes:
            process(child, level + 1, matrix)


output = svg.SVG(open(debug_svg_file_name, 'w+'))

output.begin(1000, 1000)

process(inner_svg, 0, Matrix3([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))

output.end()
