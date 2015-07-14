# Author: Sergey Vartanov (me@enzet.ru)

# Convert SVG station layout to Shape file format.

import copy
import re
import sys

sys.path.append('lib')

import path
import svg
import vector

from xml.dom import minidom

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


def process(root, level, matrix):
    if isinstance(root, minidom.Text):
        return
    # print (' ' * (level * 2)) + repr(root.localName)
    if 'transform' in root.attributes.keys():
        new_matrix = None
        m = re.match('^translate\((?P<x>[0-9.-]*),(?P<y>[0-9.-]*)\)$', root.attributes['transform'].value)
        if m:
            new_matrix = vector.Matrix3([[1, 0, float(m.group('x'))],
                                        [0, 1, float(m.group('y'))],
                                        [0, 0, 1]])
        m = re.match('^matrix\((?P<a>[0-9.-]*),(?P<b>[0-9.-]*),(?P<c>[0-9.-]*),(?P<d>[0-9.-]*),(?P<e>[0-9.-]*),(?P<f>[0-9.-]*)\)$', root.attributes['transform'].value)
        if m:
            new_matrix = vector.Matrix3([[float(m.group('a')), float(m.group('c')), float(m.group('e'))],
                                        [float(m.group('b')), float(m.group('d')), float(m.group('f'))],
                                        [0, 0, 1]])
        if new_matrix:
            matrix = copy.deepcopy(matrix) * new_matrix
    if root.localName == 'g':
        a = 0
        for child in root.childNodes:
            if child.localName == 'path':
                a += 1
        if a == 8 or a == 3:
            print 'stairs'
    if root.localName == 'path':
        str_matrix = None
        if matrix:
            str_matrix = 'matrix(' + str(matrix.matrix[0][0]) + ',' + str(matrix.matrix[1][0]) + ',' + \
                                                                      str(matrix.matrix[0][1]) + ',' + str(matrix.matrix[1][1]) + ',' + \
                                                                      str(matrix.matrix[0][2]) + ',' + str(matrix.matrix[1][2]) + ')'
        current_path = root.attributes['d'].value
        p = path.Path()
        p.parse_from_svg(current_path)
        p.transform(matrix)
        fixed_path = p.to_svg()
        output.path(current_path, transform=str_matrix, width=2)
        output.path(fixed_path, color='FF0000')
    for child in root.childNodes:
        process(child, level + 1, matrix)


output = svg.SVG(open(debug_svg_file_name, 'w+'))

output.begin(1000, 1000)

process(inner_svg, 0, vector.Matrix3([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))

output.end()
