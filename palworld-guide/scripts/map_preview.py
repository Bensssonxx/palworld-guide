#!/usr/bin/env python3
"""Optional PNG export using existing Pillow and rsvg-convert; never installs them."""
import argparse
import base64
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def checked_svg(body):
    """Only the static, self-contained elements emitted by map_tools are accepted."""
    if len(body) > 32_000_000 or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        raise ValueError('Expected a bounded static map SVG without XML declarations of entities')
    root = ET.fromstring(body)
    allowed = {'svg', 'defs', 'clipPath', 'rect', 'g', 'text', 'image', 'path', 'circle', 'title', 'a'}
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('Expected an SVG map')
    for dimension in ('width', 'height'):
        value = float(root.get(dimension, '0'))
        if not 1 <= value <= 4096:
            raise ValueError('Unexpected map canvas dimensions')
    images = []
    for element in root.iter():
        tag = element.tag.rsplit('}', 1)[-1]
        if tag not in allowed:
            raise ValueError('Unsupported SVG element')
        for key, value in element.attrib.items():
            local = key.rsplit('}', 1)[-1].lower()
            if local.startswith('on') or local == 'style' or 'url(' in value.lower():
                # Only the generated local clipping reference is needed.
                if not (local == 'clip-path' and value == 'url(#mapclip)'):
                    raise ValueError('Active or external SVG content is unsupported')
            if local == 'href' and tag != 'a':
                if tag != 'image' or not value.startswith(('data:image/webp;base64,', 'data:image/png;base64,')):
                    raise ValueError('Export requires embedded map tiles; no external image requests are made')
        if tag == 'image':
            value = element.get('href', '')
            if not value.startswith(('data:image/webp;base64,', 'data:image/png;base64,')):
                raise ValueError('Missing embedded tile')
            raw = base64.b64decode(value.split(',', 1)[1], validate=True)
            if len(raw) > 2_000_000:
                raise ValueError('Map tile exceeds export limit')
            images.append((element, raw))
    if not images:
        raise ValueError('No embedded terrain; refusing a marker-only PNG')
    return root, images


def export(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('Output exists; preserve it and choose a new path')
    if output.suffix.lower() != '.png':
        raise ValueError('Choose a PNG output path')
    root, images = checked_svg(source.read_bytes())
    renderer = shutil.which('rsvg-convert')
    if not renderer:
        raise ValueError('Optional rsvg-convert is unavailable; open the original SVG in a modern browser')
    try:
        from PIL import Image
    except ImportError as error:
        raise ValueError('Optional Pillow is unavailable in this Python; use an existing compatible interpreter or open the original SVG in a modern browser') from error
    for element, raw in images:
        with Image.open(io.BytesIO(raw)) as tile:
            if tile.width > 4096 or tile.height > 4096:
                raise ValueError('Unexpected map tile dimensions')
            converted = io.BytesIO()
            tile.save(converted, format='PNG')
        element.set('href', 'data:image/png;base64,' + base64.b64encode(converted.getvalue()).decode('ascii'))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.map-export-', dir=output.parent) as temporary:
        folder = Path(temporary)
        (folder/'map.svg').write_bytes(ET.tostring(root, encoding='utf-8'))
        env = os.environ.copy()
        env['TMPDIR'] = str(folder)
        process = subprocess.run([renderer, str(folder/'map.svg'), '-o', str(folder/'map.png')],
                                 capture_output=True, timeout=45, env=env)
        if process.returncode or not (folder/'map.png').is_file():
            raise ValueError('Optional SVG renderer failed; preserve the original SVG')
        # Exclusive creation preserves an existing output even in a concurrent run.
        with output.open('xb') as handle:
            handle.write((folder/'map.png').read_bytes())
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--svg', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        print(export(args.svg, args.output))
    except (ValueError, OSError, ET.ParseError, subprocess.TimeoutExpired) as error:
        parser.exit(2, str(error)+'\n')
