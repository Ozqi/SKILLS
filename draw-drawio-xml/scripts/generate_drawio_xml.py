#!/usr/bin/env python3
"""Generate draw.io XML architecture diagrams from a simple JSON topology."""
import argparse
import json
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

STYLE_MAP = {
    "client": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "gateway": "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;fixedSize=1;fillColor=#dbeafe;strokeColor=#3b82f6;",
    "service": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "module": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "worker": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "repo": "rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;",
    "mq": "shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
    "storage": "shape=cylinder3d;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#e1d5e7;strokeColor=#9673a6;",
    "db": "shape=cylinder3d;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#e1d5e7;strokeColor=#9673a6;",
    "cache": "shape=cylinder3d;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#dbeafe;strokeColor=#6366f1;",
    "external": "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;",
    "config": "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#ffe6cc;strokeColor=#d79b00;",
    "function": "ellipse;whiteSpace=wrap;html=1;fillColor=#e6f2ff;strokeColor=#4d80b3;",
}
EDGE_STYLE = "rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeColor=#666666;"
DASHED_EDGE_STYLE = EDGE_STYLE + "dashed=1;"
DASHED_EDGE_TYPES = {"async", "async_event", "config", "depends_on", "optional"}


def mxcell(parent, id_, value="", style="", vertex=None, edge=None):
    cell = ET.SubElement(parent, "mxCell", {"id": id_})
    if value:
        cell.set("value", str(value))
    if style:
        cell.set("style", style)
    if vertex is not None:
        cell.set("vertex", "1")
        cell.set("parent", "1")
    if edge is not None:
        cell.set("edge", "1")
        cell.set("parent", "1")
    return cell


def add_geometry(cell, x=0, y=0, w=160, h=70, as_="geometry"):
    geom = ET.SubElement(cell, "mxGeometry", {
        "x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": as_
    })
    return geom


def get_value(item, *keys, default=None):
    for key in keys:
        if key in item:
            return item[key]
    return default


def normalize_data(data):
    nodes = data.get("nodes", data.get("节点", []))
    edges = data.get("edges", data.get("边", []))
    return {
        "title": data.get("title", data.get("拓扑", data.get("名称", "Architecture"))),
        "nodes": nodes,
        "edges": edges,
    }


def normalize_nodes(data):
    nodes = data.get("nodes", [])
    for i, n in enumerate(nodes):
        n.setdefault("id", f"n{i+1}")
        n.setdefault("label", get_value(n, "label", "名称", "name", default=n["id"]))
        n.setdefault("type", get_value(n, "type", "类型", default="service"))
        n.setdefault("x", 80 + (i % 4) * 240)
        n.setdefault("y", 80 + (i // 4) * 140)
        n.setdefault("width", 170)
        n.setdefault("height", 70)
    return nodes


def build_drawio(data):
    data = normalize_data(data)
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "modified": "2026-07-28T00:00:00.000Z", "agent": "Aime", "version": "24.7.17"})
    diagram = ET.SubElement(mxfile, "diagram", {"id": uuid.uuid4().hex[:12], "name": data.get("title", "Architecture")})
    model = ET.SubElement(diagram, "mxGraphModel", {"dx": "1200", "dy": "800", "grid": "1", "gridSize": "10", "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "1", "pageScale": "1", "pageWidth": "1169", "pageHeight": "827", "math": "0", "shadow": "0"})
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    node_ids = set()
    for node in normalize_nodes(data):
        node_ids.add(node["id"])
        base_style = STYLE_MAP.get(node.get("type", "service"), STYLE_MAP["service"])
        if node.get("style"):
            base_style += node["style"]
        cell = mxcell(root, node["id"], node.get("label", node["id"]), base_style, vertex=True)
        add_geometry(cell, node.get("x", 0), node.get("y", 0), node.get("width", 170), node.get("height", 70))

    for i, edge in enumerate(data.get("edges", [])):
        src, dst = edge.get("from"), edge.get("to")
        if src not in node_ids or dst not in node_ids:
            raise ValueError(f"edge {i} references unknown node: {src!r} -> {dst!r}")
        edge_type = get_value(edge, "type", "关系", default="")
        style = DASHED_EDGE_STYLE if edge.get("dashed") or edge_type in DASHED_EDGE_TYPES else EDGE_STYLE
        if edge.get("style"):
            style += edge["style"]
        cell = mxcell(root, edge.get("id", f"e{i+1}"), get_value(edge, "label", "名称", default=""), style, edge=True)
        cell.set("source", src)
        cell.set("target", dst)
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})

    return ET.tostring(mxfile, encoding="unicode", method="xml")


def main():
    parser = argparse.ArgumentParser(description="Generate draw.io XML from JSON topology")
    parser.add_argument("input", help="Input topology JSON file")
    parser.add_argument("-o", "--output", default="architecture.drawio", help="Output .drawio/.xml path")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    xml = build_drawio(data)
    Path(args.output).write_text(xml, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
