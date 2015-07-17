# Author: Sergey Vartanov (me@enzet.ru)

# Convert SVG station layout to Shape file format.

import copy
import math
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


def get_min(vector_1, vector_2):
    return Vector(min(vector_1.x, vector_2.x), min(vector_1.y, vector_2.y))


def get_max(vector_1, vector_2):
    return Vector(max(vector_1.x, vector_2.x), max(vector_1.y, vector_2.y))


def get_segment_length(segment):
    return math.sqrt((segment.end.x - segment.start.x) ** 2 + \
                     (segment.end.y - segment.start.y) ** 2)


def get_path_length(path):
    length = 0
    for segment in path.segments:
        length += get_segment_length(segment)
    return length


def get_segment_bounds(segment):
    minimum = segment.start
    maximum = segment.start
    minimum = get_min(minimum, segment.end)
    maximum = get_max(maximum, segment.end)
    if segment.middle_1:
        minimum = get_min(minimum, segment.middle_1)
        maximum = get_max(maximum, segment.middle_1)
    if segment.middle_2:
        minimum = get_min(minimum, segment.middle_2)
        maximum = get_max(maximum, segment.middle_2)
    return minimum, maximum


def get_path_bounds(path):
    minimum = Vector(1000, 1000)
    maximum = Vector(-1000, -1000)
    for s in path.segments:
        segment_minimum, segment_maximum = get_segment_bounds(s)
        minimum = get_min(minimum, segment_minimum)
        maximum = get_max(maximum, segment_maximum)
    return minimum, maximum


def eq(a, b):
    return abs(a - b) < 1.0


def get_bounds(paths):

    def get_for(get_component):
        min_c, p_min = 1000, None
        max_c, p_max = -1000, None
        for p in paths:
            path_minimum, path_maximum = get_path_bounds(p)
            if get_component(path_minimum) < min_c: 
                min_c, p_min = get_component(path_minimum), p
            if get_component(path_maximum) > max_c: 
                max_c, p_max = get_component(path_maximum), p
        return min_c, max_c, p_min, p_max

    min_x, max_x, p_min, p_max = get_for(lambda a: a.x)

    ppmin, _ = get_path_bounds(p_min)
    ppmax, _ = get_path_bounds(p_max)
    if eq(ppmin.x, ppmax.x):
        min_y, max_y, p_min, p_max = get_for(lambda a: a.y)

    return p_min, p_max


def process(root, level, matrix):
    """
    Process SVG element.
    """
    global ways, way_count, nodes, node_count
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
            paths = []
            for child in root.childNodes:
                if child.localName == 'path':
                    paths.append(extract_path(child, matrix))
            is_stairs = True
            length = get_path_length(paths[0])
            for p in paths[1:]:
                if not eq(length, get_path_length(p)):
                    is_stairs = False
            if is_stairs:
                print 'Stairs detected.'
                p_min, p_max = get_bounds(paths)
                x_1 = (p_min.segments[0].start.x + p_min.segments[0].end.x) / 2.0
                y_1 = (p_min.segments[0].start.y + p_min.segments[0].end.y) / 2.0
                x_2 = (p_max.segments[0].start.x + p_max.segments[0].end.x) / 2.0
                y_2 = (p_max.segments[0].start.y + p_max.segments[0].end.y) / 2.0
                way_count += 1
                ways[way_count] = {'id': way_count, 'type': 'stairs',
                                   'nodes': [node_count + 1, node_count + 2]}
                node_count += 1
                nodes[node_count] = {'id': node_count, 'x': x_1, 'y': y_1}
                node_count += 1
                nodes[node_count] = {'id': node_count, 'x': x_2, 'y': y_2}
        else:
            for child in root.childNodes:
                process(child, level + 1, matrix)
    elif root.localName == 'path':
        p = extract_path(root, matrix)
        # output.path(p.to_svg(), color='FF0000', width=0.2)
    else:
        for child in root.childNodes:
            process(child, level + 1, matrix)


def draw(output, nodes, ways):
    c = '2288DD'
    w = 0.5
    for way_id in ways:
        way = ways[way_id]
        if way['type'] == 'stairs':
            for i in range(1, len(way['nodes'])):
                node_1 = nodes[way['nodes'][i - 1]]
                node_2 = nodes[way['nodes'][i]]
                output.line(node_1['x'], node_1['y'], node_2['x'], node_2['y'], width=w, color=c)
    for node_id in nodes:
        count = 0
        for way_id in ways:
            if node_id in ways[way_id]['nodes']:
                count += 1
        node = nodes[node_id]
        if count != 0:
            output.circle(node['x'], node['y'], 0.5 + 0.5 * count, width=w, color=c, fill='FFFFFF')


# Actions

output = svg.SVG(open(debug_svg_file_name, 'w+'))

output.begin(1000, 1000)

node_count = 0
nodes = {}
way_count = 0
ways = {}
process(inner_svg, 0, Matrix3([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
draw(output, nodes, ways)

output.end()
