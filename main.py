import sys
import os
from typing import Dict
from collections import OrderedDict
import unicodedata
import logging
from contextlib import contextmanager

original_cwd = os.getcwd()
path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(path, "gitstats"))

import gitstats

logger = logging.getLogger(__name__)


def merge_author(a1, a2):
    # TODO: Needs to merge more properties
    a1["commits"] += a2["commits"]
    a1["lines_added"] += a2["lines_added"]
    a1["lines_removed"] += a2["lines_removed"]

    return a1


def getAuthorInfos(data) -> Dict[str, dict]:
    names = data.getAuthors()

    authorInfos = {}
    for name in names:
        _authorInfo = data.getAuthorInfo(name)

        # Run the following and be amazed by the power of Unicode:
        #   bool('å' == "å")  # False
        # This weird unicode char was in Måns name, so now we have to unicode normalize everything.
        # Never done this before, so thanks for making me learn Måns, or perhaps should I write Måns.
        _new_name = unicodedata.normalize('NFKC', name)
        if _new_name != name:
            logger.info("Name '{}' was normalized to '{}'".format(name, _new_name))
            name = _new_name

        name = name.replace("å", "å")
        authorInfos[name] = _authorInfo

    author_merges = [("Johan Bjäreholt", "johan-bjareholt")]
    for a1_name, a2_name in author_merges:
        if a1_name in authorInfos and a2_name in authorInfos:
            a1 = authorInfos.pop(a1_name)
            a2 = authorInfos.pop(a2_name)
            authorInfos[a1_name] = merge_author(a1, a2)

    return authorInfos


def generateForRepo(path):
    path = os.path.abspath(path)

    # TODO: Could use caching to speed up
    data = gitstats.GitDataCollector()

    # `data.collect` always gets the current directory for whatever reason,
    # os.chdir works as a workaround
    os.chdir(path)
    data.collect(path)
    os.chdir(original_cwd)

    data.refine()

    print(data.projectname)
    print("Active days: {}".format(len(data.getActiveDays())))

    rows = []
    authorInfos = getAuthorInfos(data)
    for name, info in authorInfos.items():
        row = OrderedDict(name=name,
                          commits=info["commits"],
                          lines_added=info["lines_added"],
                          lines_removed=info["lines_removed"])

        rows.append(row)

    return rows


def table_print(rows):
    print("{name:<21} | {commits:<8} | {adds:<8} | {deletes:<8}".format(name="Name", commits="Commits", adds="Added", deletes="Removed"))
    for row in rows:
        print("{name:<21} | {commits:<8} | +{lines_added:<7} | -{lines_removed:<7}".format(**row))


class HTML:
    def __init__(self):
        self.s = ""
        self.indent_level = 0
        self.inline_mode = False

    @contextmanager
    def tag(self, tag_type, inline=False):
        self += "<{}>".format(tag_type)
        self.indent_level += 1
        yield
        self.indent_level -= 1
        self += "</{}>".format(tag_type)

    def __iadd__(self, other):
        self.s += "\n" + (self.indent_level * "    ") + other
        return self


def table2html(rows):
    html = HTML()
    with html.tag("table"):
        # Header
        with html.tag("tr"):
            for key in rows[0]:
                html += "<th>{}</th>".format(key)

        for row in rows:
            with html.tag("tr"):
                for key in rows[0]:
                    html += "<td>{}</td>".format(row[key])
    return html.s


def save_table(name, rows, directory="tables"):
    if not os.path.exists(directory):
        os.makedirs(directory)
    filename = "{}.html".format(name)
    filepath = os.path.join("tables", filename)
    with open(filepath, "w") as f:
        f.write(html)


if __name__ == "__main__":
    for repopath in sys.argv[1:]:
        rows = generateForRepo(repopath)
        for row in rows:
            # print(row)
            pass

        table_print(rows)

        table_name = os.path.dirname(repopath)
        html = table2html(rows)
        save_table(table_name, html)
        print(html)

        print("=" * 60)
