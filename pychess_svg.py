import pychess
import math
import os
from typing import Dict, Tuple, Union

import svgutils
from lxml.etree import tostring

import xml.etree.ElementTree as ET


SQUARE_SIZE = 45
MARGIN = 20

SVG_PIECES = {}
SVG_PATH_PIECES = {}


XX = """<g id="xx"><path d="M35.865 9.135a1.89 1.89 0 0 1 0 2.673L25.173 22.5l10.692 10.692a1.89 1.89 0 0 1 0 2.673 1.89 1.89 0 0 1-2.673 0L22.5 25.173 11.808 35.865a1.89 1.89 0 0 1-2.673 0 1.89 1.89 0 0 1 0-2.673L19.827 22.5 9.135 11.808a1.89 1.89 0 0 1 0-2.673 1.89 1.89 0 0 1 2.673 0L22.5 19.827 33.192 9.135a1.89 1.89 0 0 1 2.673 0z" fill="#000" stroke="#fff" stroke-width="1.688"/></g>"""  # noqa: E501

CHECK_GRADIENT = """<radialGradient id="check_gradient" r="0.5"><stop offset="0%" stop-color="#ff0000" stop-opacity="1.0" /><stop offset="50%" stop-color="#e70000" stop-opacity="1.0" /><stop offset="100%" stop-color="#9e0000" stop-opacity="0.0" /></radialGradient>"""  # noqa: E501

DEFAULT_COLORS = {
    "square light": "#f0d9b5",
    "square dark": "#b58863",
    "square dark lastmove": "#aaa23b",
    "square light lastmove": "#cdd16a",
    "margin": "#212121",
    "inner border": "#111",
    "outer border": "#111",
    "coord": "#333333",
    "arrow green": "#15781B80",
    "arrow red": "#88202080",
    "arrow yellow": "#e68f00b3",
    "arrow blue": "#00308880",
}


STATIC_PATH = "pychess-variants/static/"


def get_svg_pieces_from_css(css):
    SVG_PIECES[css] = {}
    SVG_PATH_PIECES[css] = {}
    css_path = os.path.join(STATIC_PATH, "piece", css + ".css")
    if not os.path.isfile(css_path):
        print("ERROR: FileNotFoundError %s" % css_path)
        return
    with open(css_path) as css_file:
        color, symbol, url = "", "", ""
        promoted = False
        for line in css_file:
            if line.strip():
                if "piece." in line:
                    color = "white" if ("white" in line or "ally" in line) else "black"
                    start = line.find("piece.") + 6
                    end = line.find("-piece")
                    symbol = line[start:end]
                    if "promoted" in line:
                        promoted = True
                if "url" in line:
                    start = line.find("url(") + 5
                    end = line.find(")") - 1
                    url = line[start:end]
                if symbol and url:
                    if color == "white":
                        letters = list(symbol)
                        letters[-1] = letters[-1].upper()
                        symbol = ''.join(letters)
                    if promoted:
                        symbol = "p" + symbol
                    SVG_PATH_PIECES[css][symbol] = url
                    color, symbol, url = "", "", ""
                    promoted = False


def square_file(square):
    return ord(square[0]) - 97


def square_rank(square):
    return int(square[1:]) - 1


def parse_squares(board, squares):
    parsed = []
    for square in squares:
        parsed.append((board.rows - square_rank(square) - 1, square_file(square)))
    return parsed


def read_piece_svg(css, piece):
    symbol = piece.symbol
    piece_name = "%s-piece" % symbol

    if symbol not in SVG_PATH_PIECES[css]:
        return

    piece_svg = SVG_PATH_PIECES[css][symbol]

    orig_file = os.path.normpath(os.path.join(STATIC_PATH, "piece", css, "..", piece_svg))
    if not os.path.isfile(orig_file):
        print("ERROR: FileNotFoundError %s" % orig_file)
        return

    if orig_file[-3:] != "svg":
        print("ERROR: %s is not in .svg format" % orig_file)
        return

    # This can read "viewBox" but can't do scale()
    svg_full = svgutils.transform.fromfile(orig_file)

    viewBox = svg_full.root.get("viewBox")

    # This can't read "viewBox" but can do scale()
    try:
        svg = svgutils.compose.SVG(orig_file)
    except AttributeError:
        print("ERROR: Possible %s referenced in %s.css has no 'width/height'" % (orig_file, css))
        # TODO: add "width/height" to .svg
        raise

    if viewBox is not None:
        width = float(viewBox.split()[2])
    elif svg.width is not None:
        width = svg.width
    else:
        SVG_PIECES[css][symbol] = ""
        return

    if width != SQUARE_SIZE:
        new = SQUARE_SIZE / width
        svg.scale(new)

    head = """<g id="%s-%s">""" % (pychess.COLOR_NAMES[piece.color], piece_name)
    tail = """</g>"""

    SVG_PIECES[css][symbol] = "%s%s%s" % (head, tostring(svg.root), tail)


class SvgWrapper(str):
    def _repr_svg_(self):
        return self


def _svg(viewbox_x, viewbox_y, width, height):
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "viewBox": "0 0 %d %d" % (viewbox_x, viewbox_y),
    })

    if width is not None:
        svg.set("width", str(width))
    if height is not None:
        svg.set("height", str(height))

    return svg


def _attrs(attrs: Dict[str, Union[str, int, float, None]]) -> Dict[str, str]:
    return {k: str(v) for k, v in attrs.items() if v is not None}


def _select_color(colors: Dict[str, str], color: str) -> Tuple[str, float]:
    return _color(colors.get(color, DEFAULT_COLORS[color]))


def _color(color: str) -> Tuple[str, float]:
    if color.startswith("#"):
        try:
            if len(color) == 5:
                return color[:4], int(color[4], 16) / 0xf
            elif len(color) == 9:
                return color[:7], int(color[7:], 16) / 0xff
        except ValueError:
            pass  # Ignore invalid hex value
    return color, 1.0


def piece(css, piece, size=None):
    """
    Renders the given :class:`pychess.Piece` as an SVG image.
    """
    svg = _svg(SQUARE_SIZE, SQUARE_SIZE, size, size)
    svg.append(ET.fromstring(SVG_PIECES[css][piece.symbol]))
    return SvgWrapper(ET.tostring(svg).decode("utf-8"))


def _colors_to_css(colors: Dict[str, str]) -> str:
    """Convert a color mapping dictionary into a CSS string."""
    lines = []
    for selector, value in colors.items():
        classes = "." + ".".join(selector.split())
        lines.append(f"{classes} {{ fill: {value}; }}")
    return "\n".join(lines)


def board(css, board=None, orientation=True, flipped=False, check=None, lastmove=None, arrows=(), squares=None, width=None, height=None, colors=None, coordinates=False, borders=False, background_image=None):
    orientation ^= flipped
    inner_border = 1 if borders and coordinates else 0
    outer_border = 1 if borders else 0
    margin = 15 if coordinates else 0
    # full_size = 2 * outer_border + 2 * margin + 2 * inner_border + 8 * SQUARE_SIZE

    svg = _svg(board.cols * SQUARE_SIZE, board.rows * SQUARE_SIZE, width, height)
    if colors:
        ET.SubElement(svg, "style").text = _colors_to_css(colors)

    if lastmove:
        lastmove_from = (board.rows - square_rank(lastmove.from_square) - 1, square_file(lastmove.from_square))
        lastmove_to = (board.rows - square_rank(lastmove.to_square) - 1 , square_file(lastmove.to_square))

    defs = ET.SubElement(svg, "defs")
    if board:
        for symbol in SVG_PIECES[css]:
            defs.append(ET.fromstring(SVG_PIECES[css][symbol]))

    if squares:
        defs.append(ET.fromstring(XX))

    if check is not None:
        defs.append(ET.fromstring(CHECK_GRADIENT))
        check_rank_index = board.rows - square_rank(check) - 1
        check_file_index = square_file(check)

    # Render board background image if provided
    if background_image:
        if background_image.lower().endswith('.svg'):
            # Embed SVG background directly
            bg_path = os.path.join('pychess-variants/static/images/board', background_image)
            try:
                with open(bg_path, 'r', encoding='utf-8') as f:
                    bg_svg = f.read()
                # Remove XML declaration if present
                if bg_svg.startswith('<?xml'):
                    bg_svg = bg_svg.split('?>', 1)[-1]
                # Parse the SVG and extract width/height or viewBox
                bg_tree = ET.fromstring(bg_svg)
                if bg_tree.tag.endswith('svg'):
                    width = bg_tree.get('width')
                    height = bg_tree.get('height')
                    viewBox = bg_tree.get('viewBox')
                    if width and height:
                        try:
                            width_val = float(width.replace('px',''))
                            height_val = float(height.replace('px',''))
                        except Exception:
                            width_val = board.cols * SQUARE_SIZE
                            height_val = board.rows * SQUARE_SIZE
                    elif viewBox:
                        parts = viewBox.strip().split()
                        width_val = float(parts[2])
                        height_val = float(parts[3])
                    else:
                        width_val = board.cols * SQUARE_SIZE
                        height_val = board.rows * SQUARE_SIZE
                    # Remove <svg> wrapper, keep children
                    bg_inner = list(bg_tree)
                    bg_group = ET.Element('g')
                    for elem in bg_inner:
                        bg_group.append(elem)
                    scale_x = (board.cols * SQUARE_SIZE) / width_val
                    scale_y = (board.rows * SQUARE_SIZE) / height_val
                    bg_group.set('transform', f'translate({margin}, {margin}) scale({scale_x}, {scale_y})')
                    svg.insert(1, bg_group)
                else:
                    # fallback: insert as a group
                    bg_elem = ET.fromstring(f'<g>{bg_svg}</g>')
                    svg.insert(1, bg_elem)
            except Exception as e:
                print(f"ERROR: Could not embed SVG background: {e}")
        else:
            # Use <image> for PNG/JPG, embed as data URI
            import base64
            img_path = os.path.join('pychess-variants/static/images/board', background_image)
            try:
                with open(img_path, 'rb') as img_file:
                    img_bytes = img_file.read()
                ext = os.path.splitext(background_image)[1].lower()
                if ext == '.jpg' or ext == '.jpeg':
                    mime = 'image/jpeg'
                elif ext == '.png':
                    mime = 'image/png'
                else:
                    mime = 'application/octet-stream'
                data_uri = f"data:{mime};base64," + base64.b64encode(img_bytes).decode('ascii')
                ET.SubElement(svg, "image", {
                    "{http://www.w3.org/1999/xlink}href": data_uri,
                    "x": str(margin),
                    "y": str(margin),
                    "width": str(board.cols * SQUARE_SIZE),
                    "height": str(board.rows * SQUARE_SIZE),
                    "preserveAspectRatio": "none"
                })
            except Exception as e:
                print(f"ERROR: Could not embed PNG/JPG background: {e}")
        render_squares = False
    else:
        render_squares = True

    # Adjust SVG viewBox and size to include margin for coordinates
    if coordinates:
        total_width = board.cols * SQUARE_SIZE + 2 * margin
        total_height = board.rows * SQUARE_SIZE + 2 * margin
        svg.set("viewBox", f"0 0 {total_width} {total_height}")
        if width is not None:
            svg.set("width", str(total_width))
        if height is not None:
            svg.set("height", str(total_height))

    # Render board squares only if not using a background image
    if render_squares:
        for y_index in range(board.rows):
            for x_index in range(board.cols):
                if orientation:
                    display_row = y_index
                    display_col = x_index
                else:
                    display_row = board.rows - y_index - 1
                    display_col = board.cols - x_index - 1
                x = (x_index) * SQUARE_SIZE + (margin if coordinates else 0)
                y = (y_index) * SQUARE_SIZE + (margin if coordinates else 0)

                cls = ["square", "light" if display_col % 2 == display_row % 2 else "dark"]
                if lastmove and (display_row, display_col) in (lastmove_from, lastmove_to):
                    cls.append("lastmove")
                fill_color = DEFAULT_COLORS[" ".join(cls)]

                ET.SubElement(svg, "rect", {
                    "x": str(x),
                    "y": str(y),
                    "width": str(SQUARE_SIZE),
                    "height": str(SQUARE_SIZE),
                    "class": " ".join(cls),
                    "stroke": "none",
                    "fill": fill_color,
                })

                # Render selected squares.
                if squares and (display_row, display_col) in parse_squares(board, squares):
                    ET.SubElement(svg, "use", _attrs({
                        "href": "#xx",
                        "xlink:href": "#xx",
                        "x": x,
                        "y": y,
                    }))

    # Render coordinates using SVG <text> elements
    if coordinates:
        font_size = int(margin * 0.9)
        font_family = "Arial, sans-serif"
        text_color = DEFAULT_COLORS["coord"]
        offset = int(font_size * 0.65)  # extra padding from the board
        # Files (a-l, etc.) on bottom and top
        for file_index in range(board.cols):
            index = file_index if orientation else board.cols - file_index - 1
            file_char = pychess.COORDS[coordinates][0](index, board.cols)
            x = file_index * SQUARE_SIZE + margin + SQUARE_SIZE // 2
            y_top = offset  # more space from the board
            y_bottom = margin + board.rows * SQUARE_SIZE + offset
            for y in (y_top, y_bottom):
                ET.SubElement(svg, "text", {
                    "x": str(x),
                    "y": str(y),
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                    "font-size": str(font_size),
                    "font-family": font_family,
                    "fill": text_color,
                    "opacity": "1.0",
                }).text = file_char
        # Ranks (1-10, etc.) on left and right
        for rank_index in range(board.rows):
            index = rank_index if orientation else board.rows - rank_index - 1
            rank_char = pychess.COORDS[coordinates][1](index, board.rows)
            y = rank_index * SQUARE_SIZE + margin + SQUARE_SIZE // 2
            x_left = offset
            x_right = margin + board.cols * SQUARE_SIZE + offset
            for x in (x_left, x_right):
                ET.SubElement(svg, "text", {
                    "x": str(x),
                    "y": str(y),
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                    "font-size": str(font_size),
                    "font-family": font_family,
                    "fill": text_color,
                    "opacity": "1.0",
                }).text = rank_char
    # Render pieces
    if board is not None:
        for y_index in range(board.rows):
            for x_index in range(board.cols):
                if orientation:
                    display_row = y_index
                    display_col = x_index
                else:
                    display_row = board.rows - y_index - 1
                    display_col = board.cols - x_index - 1
                x = x_index * SQUARE_SIZE + (margin if coordinates else 0)
                y = y_index * SQUARE_SIZE + (margin if coordinates else 0)
                piece = board.piece_at(display_row, display_col)
                if piece:
                    # Render check mark.
                    if (check is not None) and check_file_index == display_col and check_rank_index == display_row:
                        ET.SubElement(svg, "rect", _attrs({
                            "x": x,
                            "y": y,
                            "width": SQUARE_SIZE,
                            "height": SQUARE_SIZE,
                            "class": "check",
                            "fill": "url(#check_gradient)",
                        }))

                    color = pychess.COLOR_NAMES[piece.color]
                    href = "#%s-%s-piece" % (color, piece.symbol)
                    ET.SubElement(svg, "use", {
                        "xlink:href": href,
                        "transform": "translate(%d, %d)" % (x, y),
                    })

    # Render arrows.
    for arrow in arrows:
        try:
            tail, head, color = arrow.tail, arrow.head, arrow.color  # type: ignore
        except AttributeError:
            tail, head = arrow  # type: ignore
            color = "green"

        try:
            color, opacity = _select_color(colors, " ".join(["arrow", color]))
        except KeyError:
            opacity = 1.0

        tail_file = square_file(tail)
        tail_rank = square_rank(tail)
        head_file = square_file(head)
        head_rank = square_rank(head)

        x_corr = board.cols - 0.5
        y_corr = board.rows - 0.5

        xtail = outer_border + (margin if coordinates else 0) + inner_border + (tail_file + 0.5 if orientation else x_corr - tail_file) * SQUARE_SIZE
        ytail = outer_border + (margin if coordinates else 0) + inner_border + (y_corr - tail_rank if orientation else tail_rank + 0.5) * SQUARE_SIZE
        xhead = outer_border + (margin if coordinates else 0) + inner_border + (head_file + 0.5 if orientation else x_corr - head_file) * SQUARE_SIZE
        yhead = outer_border + (margin if coordinates else 0) + inner_border + (y_corr - head_rank if orientation else head_rank + 0.5) * SQUARE_SIZE

        if (head_file, head_rank) == (tail_file, tail_rank):
            ET.SubElement(svg, "circle", _attrs({
                "cx": xhead,
                "cy": yhead,
                "r": SQUARE_SIZE * 0.93 / 2,
                "stroke-width": SQUARE_SIZE * 0.07,
                "stroke": color,
                "opacity": opacity if opacity < 1.0 else None,
                "fill": "none",
                "class": "circle",
            }))
        else:
            marker_size = 0.75 * SQUARE_SIZE
            marker_margin = 0.1 * SQUARE_SIZE

            dx, dy = xhead - xtail, yhead - ytail
            hypot = math.hypot(dx, dy)

            shaft_x = xhead - dx * (marker_size + marker_margin) / hypot
            shaft_y = yhead - dy * (marker_size + marker_margin) / hypot

            xtip = xhead - dx * marker_margin / hypot
            ytip = yhead - dy * marker_margin / hypot

            ET.SubElement(svg, "line", _attrs({
                "x1": xtail,
                "y1": ytail,
                "x2": shaft_x,
                "y2": shaft_y,
                "stroke": color,
                "opacity": opacity if opacity < 1.0 else None,
                "stroke-width": SQUARE_SIZE * 0.2,
                "stroke-linecap": "butt",
                "class": "arrow",
            }))

            marker = [(xtip, ytip),
                      (shaft_x + dy * 0.5 * marker_size / hypot,
                       shaft_y - dx * 0.5 * marker_size / hypot),
                      (shaft_x - dy * 0.5 * marker_size / hypot,
                       shaft_y + dx * 0.5 * marker_size / hypot)]

            ET.SubElement(svg, "polygon", _attrs({
                "points": " ".join(f"{x},{y}" for x, y in marker),
                "fill": color,
                "opacity": opacity if opacity < 1.0 else None,
                "class": "arrow",
            }))

    return SvgWrapper(ET.tostring(svg).decode("utf-8"))
