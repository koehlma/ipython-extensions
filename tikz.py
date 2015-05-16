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

import os.path

from enum import Enum
from string import Template
from subprocess import call
from tempfile import TemporaryDirectory

import IPython.core.displaypub as displaypub

import IPython.core.magic as magic
import IPython.core.magic_arguments as magic_arguments

DEFAULT_LIBRARIES = ['arrows', 'snakes', 'backgrounds', 'patterns', 'matrix',
                     'shapes', 'fit', 'calc', 'shadows', 'plotmarks']

DEFAULT_PDFLATEX = ['pdflatex', '-shell-escape', '-interaction=nonstopmode']
DEFAULT_PDF2SVG = ['pdf2svg']
DEFAULT_PDF2PNG = ['convert', '-density', '300']

latex_template = Template(r'''
\documentclass{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}

\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}

$packages

\usepackage{tikz}

$libraries

\usepackage[graphics,tightpage,active]{preview}

\PreviewEnvironment{tikzpicture}
\PreviewEnvironment{equation}
\PreviewEnvironment{equation*}

\newlength{\imagewidth}
\newlength{\imagescale}

\pagestyle{empty}
\thispagestyle{empty}

\begin{document}
$code
\end{document}''')

tikz_picture_template = Template(r'''
\begin{tikzpicture}[$options]
$code
\end{tikzpicture}
''')


class LatexError(Exception):
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

class ConvertError(Exception):
    def __init__(self, command, returncode, stderr):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr

    def __str__(self):
        return '\n'.join(['[command]', ' '.join(self.command),
                          '[returncode]', str(self.returncode),
                          '[stderr]', self.stderr.strip()])


class Format(Enum):
    SVG = 'svg'
    PNG = 'png'
    PDF = 'pdf'


def run_latex(code, command=DEFAULT_PDFLATEX):
    with TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, 'code.tex'), 'wb') as code_file:
            code_file.write(code.encode('utf-8'))
        command = command + ['code.tex']
        try:
            returncode = call(command, cwd=tempdir)
        except OSError as error:
            raise LatexError(command, -1, str(error), code)
        if returncode:
            try:
                with open(os.path.join(tempdir, 'code.log'), 'rb') as stderr:
                    error = stderr.read().decode('utf-8')
            except IOError:
                error = 'no log file created'
            raise LatexError(command, returncode, error, code)
        try:
            with open(os.path.join(tempdir, 'code.pdf'), 'rb') as pdfout:
                output = pdfout.read()
            return output
        except IOError:
            raise LatexError(command, returncode, 'no output created', code)


def convert_pdf2svg(pdf_content, command=DEFAULT_PDF2SVG):
    with TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, 'inpdf.pdf'), 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        command = command + ['inpdf.pdf', 'outsvg.svg']
        try:
            returncode = call(command, cwd=tempdir)
        except OSError as error:
            raise ConvertError(command, -1, str(error))
        if returncode:
            raise ConvertError(command, -1, '')
        try:
            with open(os.path.join(tempdir, 'outsvg.svg'), 'rb') as pdfout:
                output = pdfout.read().decode('utf-8')
            return output
        except IOError:
            raise ConvertError(command, returncode, 'no output created')


def convert_pdf2png(pdf_content, command=DEFAULT_PDF2PNG):
    with TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, 'inpdf.pdf'), 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        command = command + ['inpdf.pdf', 'outpng.png']
        try:
            returncode = call(command, cwd=tempdir)
        except OSError as error:
            raise ConvertError(command, -1, str(error))
        if returncode:
            raise ConvertError(command, -1, '')
        try:
            with open(os.path.join(tempdir, 'outpng.png'), 'rb') as pdfout:
                output = pdfout.read()
            return output
        except IOError:
            raise ConvertError(command, returncode, 'no output created')


@magic.magics_class
class TikzMagics(magic.Magics):
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '-f', '--format', default='svg', choices=('png', 'svg'),
        help='output format (png/svg)'
    )
    @magic_arguments.argument(
        '-l', '--library', nargs='*', default=DEFAULT_LIBRARIES,
        help='additional tikz libraries'
    )
    @magic_arguments.argument(
        '-p', '--package', nargs='*', default=[],
        help='additional latex packages'
    )
    @magic_arguments.argument(
        '-o', '--options', nargs='*', default=[],
        help='options passed to graphviz'
    )
    @magic_arguments.argument(
        '-s', '--save', metavar='FILENAME',
        help='save output pdf to file'
    )
    @magic.cell_magic
    def tikz(self, line, cell):
        args = magic_arguments.parse_argstring(self.tikz, line)
        fmt = Format(args.format)

        tikz_options = ' '.join(args.options)
        mapping = {'options': tikz_options, 'code': cell}
        tikz_picture = tikz_picture_template.substitute(mapping)

        latex_packages = []
        for package in args.package:
            latex_packages.append(r'\usepackage{' + package + '}')

        tikz_libraries = []
        for library in args.library + DEFAULT_LIBRARIES:
            tikz_libraries.append(r'\usetikzlibrary{' + library + '}')

        mapping = {'packages': '\n'.join(latex_packages),
                   'libraries': '\n'.join(tikz_libraries),
                   'code': tikz_picture}
        latex_document = latex_template.substitute(mapping)

        pdf_content = run_latex(latex_document)
        if args.save:
            with open(args.save, 'wb') as save_pdf:
                save_pdf.write(pdf_content)
        if fmt is Format.SVG:
            data = {'image/svg+xml': convert_pdf2svg(pdf_content)}
            displaypub.publish_display_data(data=data,
                                            metadata={'isolated' : 'true'})
        elif fmt is Format.PNG:
            return display.Image(convert_pdf2png(pdf_content))


def load_ipython_extension(ipython):
    ipython.register_magics(TikzMagics)