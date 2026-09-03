"""Minimal KSP ConfigNode (.cfg) reader shared by the JNSQ-Reborn-StockNames tools.

It keeps node headers verbatim (including ModuleManager patch syntax such as
"@Kopernicus:FOR[JNSQ-Reborn]"), preserves value order and duplicate keys, and
tolerates the usual formatting variants ("{" on the same or the next line,
"NODE {}" on one line, "//" comments, UTF-8 BOM).
"""
import re

class Node:
    __slots__ = ("header", "values", "children")

    def __init__(self, header):
        self.header = header
        self.values = []      # list of (key, value) in file order
        self.children = []    # list of Node

    @property
    def kind(self):
        """Node type without patch operators/selectors: '@Body[X]:FOR[y]' -> 'Body'."""
        h = self.header.lstrip("@!%+$-#*|&")
        return re.split(r"[\[:,]", h, 1)[0].strip()

    def get(self, key, default=None):
        for k, v in self.values:
            if k == key:
                return v
        return default

    def getall(self, key):
        return [v for k, v in self.values if k == key]

    def nodes(self, kind=None):
        return [c for c in self.children if kind is None or c.kind == kind]

    def find(self, *kinds):
        """Depth-first search for nodes whose kind matches any of kinds."""
        out = []
        for c in self.children:
            if c.kind in kinds:
                out.append(c)
            out.extend(c.find(*kinds))
        return out


def parse(text):
    root = Node("<root>")
    stack = [root]
    pending = None
    for raw in text.split("\n"):
        line = raw
        if "//" in line:
            line = line.split("//", 1)[0]
        s = line.strip()
        if not s:
            continue
        if s == "{":
            node = Node(pending if pending is not None else "")
            pending = None
            stack[-1].children.append(node)
            stack.append(node)
            continue
        if s.startswith("}"):
            if len(stack) > 1:
                stack.pop()
            rest = s[1:].strip()
            if rest.startswith("}"):
                # tolerate "}}" on one line
                while rest.startswith("}") and len(stack) > 1:
                    stack.pop()
                    rest = rest[1:].strip()
            continue
        m = re.match(r"^(.*?)\{\s*\}\s*$", s)
        if m and "=" not in m.group(1):
            stack[-1].children.append(Node(m.group(1).strip()))
            continue
        if s.endswith("{"):
            node = Node(s[:-1].strip())
            stack[-1].children.append(node)
            stack.append(node)
            continue
        if "=" in s:
            k, v = s.split("=", 1)
            stack[-1].values.append((k.strip(), v.strip()))
            continue
        pending = s
    return root


def parse_file(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return parse(f.read())
