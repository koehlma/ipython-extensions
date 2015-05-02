# -*- coding: utf-8 -*-
#
# Copyright (C) 2015, Maximilian Köhl <mail@koehlma.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

from enum import Enum
from subprocess import Popen, PIPE

import IPython.core.display as display

import IPython.core.magic as magic
import IPython.core.magic_arguments as magic_arguments


class Command(Enum):
    DOT = 'dot'
    NEATO = 'neato'
    FDP = 'fdp'
    TWOPI = 'twopi'
    CIRCO = 'circo'


class Format(Enum):
    SVG = 'svg'
    PNG = 'png'
    PDF = 'pdf'
    PS = 'ps'


_FORMAT_TO_DISPLAY = {
    Format.SVG: display.SVG,
    Format.PNG: display.Image
}


class GraphvizError(Exception):
    def __init__(self, command, returncode, stderr, code):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        self.code = code

    def __str__(self):
        return '\n'.join(['[command]', ' '.join(self.command),
                          '[returncode]', str(self.returncode),
                          '[stderr]', self.stderr.strip(),
                          '[code]', self.code.strip()])


def graphviz(code, options=[], fmt=Format.SVG, cmd=Command.DOT):
    command = [cmd.value] + options + ['-T', fmt.value]
    process = Popen(command, stdin=PIPE, stderr=PIPE, stdout=PIPE)
    try:
        stdout, stderr = process.communicate(code.encode('utf-8'))
    except (OSError, IOError) as error:
        stdout, stderr = process.stdout.read(), process.stderr.read()
        process.wait()
    if process.returncode != 0:
        stderr = stderr.decode('utf-8')
        raise GraphvizError(command, process.returncode, stderr, code)
    if fmt is Format.SVG:
        return stdout.decode('utf-8')
    return stdout


@magic.magics_class
class GraphvizMagics(magic.Magics):
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '-f', '--format', default='svg', choices=('png', 'svg'),
        help='output format (png/svg/ps/pdf)'
    )
    @magic_arguments.argument(
        '-c', '--command', default='dot',
        choices=('dot', 'neato', 'fdp', 'circo', 'twopi'),
        help='graphviz command'
    )
    @magic_arguments.argument(
        'options', default=[], nargs='*',
        help='options passed to graphviz'
    )
    @magic.cell_magic
    def graphviz(self, line, cell):
        args = magic_arguments.parse_argstring(self.graphviz, line)
        fmt = Format(args.format)
        cmd = Command(args.command)

        output = graphviz(cell, args.options, fmt, cmd)

        return _FORMAT_TO_DISPLAY[fmt](output)


def load_ipython_extension(ipython):
    ipython.register_magics(GraphvizMagics)