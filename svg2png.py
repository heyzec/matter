#!/usr/bin/env python3

import os
import re
import subprocess
import xml.etree.ElementTree as ET
import xml.dom.minidom


def inkscape_convert_svg2png(color, src_path, dst_path):
    SVG_URI = "http://www.w3.org/2000/svg"
    FRAC = 0.7
    TEMPFILE = "temp.svg"

    def parse_with_map(source):
        """Parses file, returns a tuple containing the parsed ElementTree and a namespace map (dict).

        The ElementTree object returned is the same as if parsed using xml.etree.ElementTree.parse. For
        some reason, ElementTree objects by the xml package will not provide a namespace map, unlike the
        lxml package.
        """

        root = None
        ns_map = []
        for event, node in ET.iterparse(source, events=["start-ns", "start"]):
            if event == "start-ns":
                ns_map.append(node)
            elif event == "start":
                if root is None:
                    root = node
        return (ET.ElementTree(root), dict(ns_map))

    def int_ignore_units(s):
        return int("".join(ch for ch in s if ch.isdigit()))

    def prettify(xml_string):
        return "\n".join(
            line
            for line in xml.dom.minidom.parseString(xml_string)
            .toprettyxml(indent="  ")
            .splitlines()
            if not line.isspace() and line != ""
        )

    # Fixes undefined namespace tags in output xml (not a big issue)
    dom, ns_map = parse_with_map(src_path)
    for key, value in ns_map.items():
        ET.register_namespace(key, value)

    root = dom.getroot()
    width, height = (
        int_ignore_units(root.attrib["width"]),
        int_ignore_units(root.attrib["height"]),
    )
    width_gap, height_gap = (1 - FRAC) * width / 2, (1 - FRAC) * height / 2

    # Group all elements that are children of <svg> while changing their 'style' attributes
    elements = root.findall("svg:*", namespaces={"svg": SVG_URI})
    group = ET.SubElement(root, "g")
    for element in elements:
        if any(
            map(element.tag.endswith, ["defs", "metadata"])
        ):  # Don't group these special tags
            continue
        root.remove(element)
        for (
            child
        ) in element.iter():  # Changes all decendents (.iter will also include itself)
            if "style" in child.attrib:
                child.attrib["style"] = re.sub(
                    r"(?<=fill:)\S+?(?=;)", color, child.attrib["style"]
                )
            else:
                child.attrib["style"] = f"fill:{color};"
        group.append(element)
    # Shrink the svg by a factor of FRAC for padding around icon
    group.attrib["transform"] = f"matrix({FRAC},0,0,{FRAC},{width_gap},{height_gap})"

    xml_string = ET.tostring(root).decode()
    xml_string = prettify(xml_string)
    with open(TEMPFILE, "w") as f:
        f.write(xml_string)

    # Check inkscape version
    version_string = subprocess.run(
        "inkscape --version 2>/dev/null", shell=True, stdout=subprocess.PIPE
    ).stdout.decode()
    version = re.findall(r"(?<=Inkscape )[.\d]+", version_string)[0]
    if version[0] == "1":
        arguments = [f"--export-filename={dst_path}"]
    elif version[0] == "0":
        arguments = ["--without-gui", f"--export-png={dst_path}"]
    arguments.extend([TEMPFILE, "-w", "72"])

    inkscape_proc = subprocess.Popen(
        ["inkscape", *arguments], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    subprocess.run(["sed", "s/^/inkscape: /"], stdin=inkscape_proc.stdout)
    inkscape_proc.wait()
    exit_code = inkscape_proc.returncode
    # Alternative - Using bash to pipe
    # cmd = f"""/bin/bash -c 'inkscape {' '.join(arguments)} 2>&1 | sed "s/^/inkscape: /"; exit ${{PIPESTATUS[0]}}'"""
    # exit_code = os.system(cmd)

    os.remove(TEMPFILE)
    return exit_code


def magick_convert_svg2png(color, src_path, dst_path):
    cmd = (
        r"convert -trim -scale 36x36 -extent 72x72 -gravity center "
        r"-define png:color-type=6 -background none -colorspace sRGB -channel RGB "
        rf"-threshold -1 -density 300 -fill \{color} +opaque none "
        rf"{src_path} {dst_path}"
    )
    return os.system(cmd)


# For demostration purposes
if __name__ == "__main__":
    svg2png = inkscape_convert_svg2png
    # svg2png = magick_convert_svg2png
    for file in os.listdir("./icons"):
        basename, ext = os.path.splitext(file)
        if ext == ".svg":
            svg2png("#FFFFFF", f"icons/{basename}.svg", f"icons/{basename}.png")