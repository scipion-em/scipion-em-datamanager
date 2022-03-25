# **************************************************************************
# *
# * Authors:     Irene Sanchez Lopez (isanchez@cnb.csic.es)
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************

from pwem.protocols import EMProtocol
from pyworkflow.protocol import params
from subprocess import STDOUT, PIPE, Popen

class OnedataDownloader(EMProtocol):
    """
    Downloads whole spaces, folders or files from Onedata that have been previously shared.
    """
    _label = 'Onedata downloader'

    def __init__(self, **kwargs):
        EMProtocol.__init__(self, **kwargs)

    # --------------- DEFINE param functions ---------------

    def _defineParams(self, form):
        form.addSection(label='Onedata')
        form.addParam('dataID', params.StringParam, label='Onedata space/folder/file ID', help='Onedata space, forder or file ID you want to download.')
        form.addParam('onezone', params.StringParam, label='Onezone URL', help='Onedata Onezone URL with specified protocol (ie: https://datahub.egi.eu)')
        form.addParam('downloadPath', params.PathParam, label='Download path', help='Specify the path where you want to download the data.')

    # --------------- INSERT steps functions ----------------

    def _insertAllSteps(self):
            self._insertFunctionStep('downloadDataStep')

    # --------------- STEPS functions -----------------------

    def downloadDataStep(self):
        p = Popen('cd {} && curl -s https://raw.githubusercontent.com/CERIT-SC/onedata-downloader/master/download.py | python3 - --onezone {} {}'.format(str(self.downloadPath), str(self.onezone) if str(self.onezone) != '' else 'https://datahub.egi.eu', str(self.dataID)), stdout=PIPE, stderr=STDOUT, shell=True)
        while True:
            output = p.stdout.readline().decode('utf-8')
            if output == '' and p.poll() is not None:
                break
            if output:
                l = output.rstrip()
                print(l, flush=True)
                if 'fail' in l and 'to process directory' not in l:
                    raise Exception(l)

    # --------------- INFO functions -------------------------

    def _validate(self):
        errors = []
        return errors

    def _citations(self):
        return []
        return citations

    def _summary(self):
        summary = []
        return summary

    def _methods(self):
        return []