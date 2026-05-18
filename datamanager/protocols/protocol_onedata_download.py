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
    Downloads shared datasets from Onedata environments, including complete
    spaces, folders, or individual files, into a local workspace for further
    cryo-EM processing and analysis.

    AI Generated:

    Onedata Downloader (OnedataDownloader) — User Manual
        Overview

        The Onedata Downloader protocol provides a simple mechanism for
        retrieving remotely shared datasets hosted through the Onedata
        distributed data management infrastructure. Its primary purpose is to
        allow users to import cryo-EM related data directly from collaborative
        storage environments into a local Scipion project or computational
        workspace.

        In practical research environments, cryo-EM projects are often shared
        across institutions, facilities, or computing centers. Instead of
        manually transferring files through browsers or external synchronization
        tools, this protocol enables direct access to publicly shared Onedata
        resources using a unique identifier associated with a space, folder, or
        file.

        Inputs and General Workflow

        The protocol requires three main pieces of information: the identifier
        of the shared resource, the address of the Onezone service managing the
        data federation, and a local destination path where the downloaded data
        will be stored. Once execution begins, the protocol connects to the
        specified Onedata environment and retrieves the requested content into
        the selected local directory.

        The shared identifier may correspond to a complete collaborative space,
        a specific project directory, or a single file. This flexibility makes
        the protocol suitable for many situations, ranging from downloading a
        full cryo-EM dataset to retrieving only selected reconstruction results
        or metadata files.

        Collaborative Data Access

        One of the main advantages of this protocol is its support for
        distributed scientific collaboration. Large cryo-EM datasets are often
        impractical to exchange manually due to their size and storage
        requirements. By integrating directly with Onedata services, the
        protocol simplifies data access across institutions and computing
        infrastructures.

        This approach is particularly useful in facility-based workflows where
        raw movies, processed micrographs, particle stacks, or reconstructed
        maps are deposited into shared environments immediately after
        acquisition or processing. Researchers can then retrieve only the data
        they need for downstream analysis.

        Download Scope and Organization

        Downloading an entire shared space is useful when reproducing a complete
        project or migrating an analysis workflow between systems. Downloading
        specific folders is more appropriate when users only require selected
        processing stages, such as motion-corrected micrographs, particle
        coordinates, or refinement outputs.

        Retrieval of individual files can be useful for rapid inspection or
        validation tasks, especially when working with limited local storage or
        when testing a workflow before committing to a large transfer.

        Biological and Computational Considerations

        Cryo-EM datasets can become extremely large, especially when including
        raw movies or intermediate processing products. Before starting a
        download, users should verify that the selected destination has
        sufficient storage capacity and appropriate filesystem performance.

        In collaborative projects, it is also important to maintain clear data
        organization after download. Keeping separate directories for raw data,
        preprocessing outputs, and reconstruction products improves
        reproducibility and reduces the risk of confusion during downstream
        analysis.

        Network reliability may also influence transfer performance. Large
        downloads are generally more stable on high-bandwidth institutional
        networks or computing clusters than on unstable personal connections.

        Outputs and Their Interpretation

        After successful execution, the selected Onedata content becomes
        available in the specified local directory. The downloaded files retain
        their original structure, allowing users to continue processing or
        inspection within standard cryo-EM workflows.

        Depending on the downloaded material, the retrieved data may include raw
        acquisition movies, corrected micrographs, metadata tables, particle
        stacks, masks, maps, or complete processing projects.

        Practical Recommendations

        In routine practice, users should first confirm that the shared
        identifier corresponds to the intended dataset and that access
        permissions remain active. Downloading smaller folders or selected
        subsets before retrieving a complete space can help validate the
        connection and estimate transfer times.

        For large collaborative projects, storing downloads in organized project
        directories and maintaining version consistency across collaborators is
        strongly recommended. This is especially important when downstream
        refinement, classification, or model building depends on synchronized
        datasets.

        Final Perspective

        The Onedata Downloader protocol simplifies distributed cryo-EM data
        access by bridging collaborative cloud-based storage infrastructures and
        local analysis environments. By enabling direct retrieval of shared
        datasets, it supports reproducible research, multi-institutional
        collaboration, and efficient movement of large cryo-EM data collections
        between computational platforms.
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