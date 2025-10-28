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

import os
import json
import re
from pwem import emlib, Domain
from pwem.protocols import EMProtocol
from pwem.objects import (Class2D, Class3D, Image, CTFModel, Volume, Micrograph, Movie, Particle, SetOfCoordinates, SetOfCTF, SetOfMicrographs, SetOfVolumes)
from pyworkflow.protocol import params
from pyworkflow.object import String, Set
import pyworkflow.utils as pwutils
from pyworkflow.project import config
from PIL import Image as ImagePIL
from PIL import ImageDraw
from zipfile import ZipFile, ZIP_DEFLATED
import requests
import numpy as np
import shutil
import emtable as md
from math import sqrt
from pwem.viewers import EmPlotter
from requests_toolbelt.multipart.encoder import MultipartEncoder

class CryoEMWorkflowViewerDepositor(EMProtocol):
    """
    Deposits Scipion workflows to CryoEM Workflow Viewer.
    By using it you allow your workflow and thumnbails to be uploaded to a machine hosted in the Spanish National Centre for Biotechnology (CNB).
    """
    _label = 'CryoEM Workflow Viewer deposition'
    _ih = emlib.image.ImageHandler()

    OUTPUT_WORKFLOW = 'workflow.json'
    DIR_IMAGES = 'images_representation'

    OUTPUT_NAME = 'outputName'
    OUTPUT_TYPE = 'outputType'
    OUTPUT_ITEMS = 'outputItems'
    OUTPUT_SIZE = 'outputSize'
    ITEM_ID = 'item_id'
    ITEM_REPRESENTATION = 'item_representation'


    def __init__(self, **kwargs):
        EMProtocol.__init__(self, **kwargs)
        self.response = String()

    # --------------- DEFINE param functions ---------------

    def _defineParams(self, form):
        form.addSection(label='Entry')
        form.addParam('apitoken', params.StringParam, label='API Token',
                      help='You can generate an API Token after registering at https://scipion.i2pc.es/cryoemworkflowviewer/')
        form.addParam('update', params.BooleanParam, label='Update existing entry?', default=False,
                      help='Is this an update of a previous deposition?')
        form.addParam('entryid', params.StringParam, label='Entry ID to update', condition='update',
                      help='Specify the ID of the existing entry you want to update. If you do not remember it, check it at https://scipion.i2pc.es/cryoemworkflowviewer/profile')
        form.addParam('entrytitle', params.StringParam, label='Entry title',
                      help='Specify a descriptive entry title')
        form.addParam('entrydescription', params.TextParam, label='Entry description',
                      help='Specify a description for the entry')
        form.addParam('public', params.BooleanParam, label='Make entry public?', default=False,
                      help='Do you want the entry be publicly visible at https://scipion.i2pc.es/cryoemworkflowviewer/public_entries ?')

    # --------------- INSERT steps functions ----------------

    def _insertAllSteps(self):
            self._insertFunctionStep('createDepositionStep')
            self._insertFunctionStep('makeDepositionStep')

    # --------------- STEPS functions -----------------------

    def createDepositionStep(self):
        # make thumbnails folder in extra
        pwutils.makePath(self._getExtraPath(self.DIR_IMAGES))

        # export workflow json
        self.exportWorkflow()

        # zip thumbnails folder
        zipObj = ZipFile(self._getExtraPath(pwutils.replaceBaseExt(self.DIR_IMAGES, 'zip')), 'w', ZIP_DEFLATED)
        rootlen = len(self._getExtraPath(self.DIR_IMAGES)) + 1
        for base, dirs, files in os.walk(self._getExtraPath(self.DIR_IMAGES)):
            for file in files:
                fn = os.path.join(base, file)
                zipObj.write(fn, fn[rootlen:])

    def makeDepositionStep(self):
        workflow = open(self._getExtraPath(self.OUTPUT_WORKFLOW), 'rb')
        thumbnails = open(self._getExtraPath(pwutils.replaceBaseExt(self.DIR_IMAGES, 'zip')), 'rb')
        url = 'https://scipion.i2pc.es/cryoemworkflowviewer/uploaddata/%s/%s/%s/%s%s' % (self.apitoken, '1' if self.public else '0', self.entrytitle, self.entrydescription, '/' + str(self.entryid) if self.update else '')

        data = MultipartEncoder(fields = {'workflow': ('workflow.json', workflow, 'application/json'),
                                          'thumbnails': ('images_representation.zip', thumbnails, 'application/zip')})

        response = requests.post(url, data=data, headers={'Content-Type': data.content_type}, verify=False)

        self.response.set(str(response.text))
        self._store()
        print(self.response)

        if response.status_code != 201:
            raise Exception('The submission was not ok: %s' % self.response)

    # --------------- INFO functions -------------------------

    def _validate(self):
        errors = []
        if self.apitoken == '':
            errors.append('You have to provide an API Token (yo can get one at https://scipion.i2pc.es/cryoemworkflowviewer/profile )')
        if self.entrytitle == '':
            errors.append('You have to provide a title for the entry')
        if self.entrydescription == '':
            errors.append('You have to provide a description for the entry')
        if self.update and self.entryid == '':
            errors.append('You have to provide the ID of the entry you want to update. If you do not remember it, check it at https://scipion.i2pc.es/cryoemworkflowviewer/profile')
        return errors

    def _citations(self):
        citations = []
        return citations

    def _summary(self):
        summary = []
        if self.response.get():
            summary.append("Deposition result: %s" % (self.response))
        else:
            summary.append('No deposition done yet')
        return summary

    def _methods(self):
        return []

    # -------------------- UTILS functions -------------------------

    def getTopLevelPath(self, *paths):
        return self._getExtraPath(*paths)

    def getProjectPath(self, *paths):
        return self.getProject().getPath(*paths)

    def exportWorkflow(self):
        project = self.getProject()
        workflowProts = project.getRuns()
        workflowProts = [prot for prot in workflowProts if prot.getObjId() != self.getObjId()]  # remove current protocol

        workflowJsonPath = self.getProjectPath(self.getTopLevelPath(self.OUTPUT_WORKFLOW))
        protDicts = project.getProtocolsDict(workflowProts)

        # labels and colors
        settingsPath = self.getProjectPath(project.settingsPath)
        settings = config.ProjectSettings.load(settingsPath)
        labels = settings.getLabels()
        labelsDict = {}
        for label in labels:
            labelInfo = label._values
            labelsDict[labelInfo['name']] = labelInfo['color']

        protsConfig = settings.getNodes()
        protsLabelsDict = {}
        for protConfig in protsConfig:
            protConfigInfo = protConfig._values
            if len(protConfigInfo['labels']) > 0:
                protsLabelsDict[protConfigInfo['id']] = []
                for label in protConfigInfo['labels']:
                    protsLabelsDict[protConfigInfo['id']].append(label)

        # Add extra info to protocosDict
        for prot in workflowProts:
            objId = prot.getObjId()
            # Get summary and add input and output information
            summary = prot.summary()
            for a, item in prot.iterInputAttributes():
                if item.isPointer():
                    try:
                        inputLabel = protDicts[int(item.getUniqueId().split('.')[0])]['object.label']
                        inputLabel = f" (from {inputLabel}) "
                    except:
                        inputLabel = ''
                itemName = item.getUniqueId() if item.isPointer() else item.getObjName()
                summary.append(f"Input: {itemName}{inputLabel} - {str(item.get())}")

            protDicts[objId]['output'] = []

            for a, output in prot.iterOutputAttributes():
                protDicts[objId]['output'].append(self.getOutputDict(output))
                summary.append(f"Output: {output.getObjName()} - {str(output)}")

            protDicts[objId]['summary'] = '\n'.join(summary)

            # additional plots
            additionalPlots = self.getAdditionalPlots(prot)
            for plotName, plotPath in additionalPlots.items():
                protDicts[objId]['output'].append({self.OUTPUT_NAME: plotName,
                                                   self.OUTPUT_ITEMS: [{self.ITEM_REPRESENTATION: plotPath}]})


            # Get log (stdout)
            outputs = []
            stdout = prot.getStdoutLog()
            if pwutils.exists(stdout):
                logPath = self.getTopLevelPath(self.DIR_IMAGES,
                                               "%s_%s.log" % (objId, prot.getClassName()))
                pwutils.copyFile(stdout, logPath)
                outputs = logPath

            protDicts[objId]['log'] = outputs

            # labels
            if objId in protsLabelsDict.keys():
                protDicts[objId]['label'] = protsLabelsDict[objId]
                protDicts[objId]['labelColor'] = []
                for label in protDicts[objId]['label']:
                    protDicts[objId]['labelColor'].append(labelsDict[label])

            # Get plugin and binary version
            try:
                protDicts[objId]['plugin'] = prot.getPlugin().getName()
                package = self.getClassPackage()
                if hasattr(package, "__version__"):
                    protDicts[objId]['pluginVersion'] = package.__version__
                protDicts[objId]['pluginBinaryVersion'] = prot.getPlugin().getActiveVersion()
            except:
                pass

        with open(workflowJsonPath, 'w') as f:
            f.write(json.dumps(list(protDicts.values()), indent=4, separators=(',', ': ')))

    # --------------- imageSet utils -------------------------

    def getOutputDict(self, output):
        self.outputName = output.getObjName()
        outputDict = {
            self.OUTPUT_NAME: output.getObjName(),
            self.OUTPUT_TYPE: output.getClassName()
        }
        items = []

        # If output is a Set get a list with all items
        if isinstance(output, Set):
            outputDict[self.OUTPUT_SIZE] = output.getSize()
            count = 0
            if isinstance(output, SetOfCoordinates):
                coordinatesDict = {}
                for micrograph in output.getMicrographs():  # get the first three micrographs
                    micFn = micrograph.getFileName()
                    count += 1
                    repPath = self.getTopLevelPath(self.DIR_IMAGES, '%s_%s' % (
                        self.outputName, pwutils.replaceBaseExt(micFn, 'jpg')))
                    self.createThumbnail(micFn, repPath, type=Micrograph)
                    coordinatesDict[micrograph.getMicName()] = {'path': repPath,
                                                                'Xdim': micrograph.getXDim(),
                                                                'Ydim': micrograph.getYDim()}

                    items.append({self.ITEM_REPRESENTATION: repPath})
                    if count == 3: break

                for coordinate in output:  #  for each micrograph, get its coordinates
                    if coordinate.getMicName() in coordinatesDict:
                        coordinatesDict[coordinate.getMicName()].setdefault('coords', []).append([coordinate.getX(), coordinate.getY()])

                for micrograph, values in coordinatesDict.items():  # draw coordinates in micrographs jpgs
                    if 'coords' in values:
                        image = ImagePIL.open(values['path']).convert('RGB')
                        W_mic = values['Xdim']
                        H_mic = values['Ydim']
                        W_jpg, H_jpg = image.size
                        draw = ImageDraw.Draw(image)
                        r = W_jpg / 256
                        for coord in values['coords']:
                            x = coord[0] * (W_jpg / W_mic)
                            y = coord[1] * (H_jpg / H_mic)
                            draw.ellipse((x - r, y - r, x + r, y + r), fill=(0, 255, 0))
                        image.save(values['path'], quality=95)

            else:
                for item in output.iterItems():
                    count += 1
                    itemDict = self.getItemDict(item, count)
                    items.append(itemDict)
                    # In some types get only a limited number of items
                    if (isinstance(item, Micrograph) or isinstance(item, Movie) or isinstance(item, CTFModel)) and count == 3: break
                    if isinstance(item, Particle) and count == 15: break

        # If it is a single object then only one item is present
        else:
            items.append(self.getItemDict(output))

        outputDict[self.OUTPUT_ITEMS] = items

        return outputDict

    def getItemDict(self, item, count=None):
        attributes = item.getAttributes()
        # Skip attributes that are Pointer
        itemDict = {k: str(v) for k, v in attributes if not v.isPointer()}
        itemDict[self.ITEM_ID] = item.getObjId()

        try:
            # Get item representation
            if isinstance(item, Class2D):
                # use representative as item representation
                rep = item.getRepresentative()
                repPath = self.getTopLevelPath(self.DIR_IMAGES, '%s_%s_%s' % (
                    self.outputName, rep.getIndex(),
                    pwutils.replaceBaseExt(rep.getFileName(), 'jpg')))
                self._ih.convert(rep.getLocation(), self.getProjectPath(repPath))

                if '_size' in itemDict:  # write number of particles over the class
                    text = itemDict['_size'] + " ptcls"
                    image = ImagePIL.open(repPath).convert('RGB')
                    W, H = image.size
                    draw = ImageDraw.Draw(image)
                    draw.text((5, H - 15), text, fill=(0, 255, 0))
                    image.save(repPath, quality=95)

                itemDict[self.ITEM_REPRESENTATION] = repPath

            elif isinstance(item, Class3D):
                itemFn = item.getFileName()
                # Get all slices in x,y and z directions of representative to represent the class
                rep = item.getRepresentative()
                repDir = self.getTopLevelPath(self.DIR_IMAGES,
                                              '%s_%s' % (self.outputName,
                                                         pwutils.removeBaseExt(rep.getFileName())))
                pwutils.makePath(repDir)
                if itemFn.endswith('.mrc'):
                    item.setFileName(itemFn + ':mrc')
                V = emlib.Image(rep.getFileName()).getData()
                self.writeSlices(V, os.path.join(repDir, 'slicesX'), 'X')
                self.writeSlices(V, os.path.join(repDir, 'slicesY'), 'Y')
                self.writeSlices(V, os.path.join(repDir, 'slicesZ'), 'Z')

                if '_size' in itemDict:  # write number of particles over a class image
                    text = itemDict['_size'] + " ptcls"
                    image = ImagePIL.open(os.path.join(repDir, 'slicesX_0000.jpg')).convert('RGB')
                    W, H = image.size
                    draw = ImageDraw.Draw(image)
                    draw.text((5, H - 15), text, fill=(0, 255, 0))
                    image.save(os.path.join(repDir, 'slicesX_0000.jpg'), quality=95)

                itemDict[self.ITEM_REPRESENTATION] = [os.path.join(repDir, file) for file in sorted(os.listdir(repDir))]

            elif isinstance(item, Volume):
                itemFn = item.getFileName()
                # if is a .vol volume, convert to .mrc
                if itemFn.endswith(".vol"):
                    repPath = self.getTopLevelPath(self.DIR_IMAGES,
                                                   f"{self.outputName}_{pwutils.removeBaseExt(itemFn)}.mrc")
                    self._ih.convert(itemFn, self.getProjectPath(repPath))

                # Get all slices in x,y and z directions to represent the volume
                repDir = self.getTopLevelPath(self.DIR_IMAGES,
                                              f"{self.outputName}_{pwutils.removeBaseExt(itemFn)}")
                pwutils.makePath(repDir)
                if itemFn.endswith('.mrc'):
                    item.setFileName(itemFn + ':mrc')
                V = emlib.Image(itemFn).getData()
                self.writeSlices(V, os.path.join(repDir, 'slicesX'), 'X')
                self.writeSlices(V, os.path.join(repDir, 'slicesY'), 'Y')
                self.writeSlices(V, os.path.join(repDir, 'slicesZ'), 'Z')

                itemDict[self.ITEM_REPRESENTATION] = [os.path.join(repDir, file) for file in sorted(os.listdir(repDir))]

            elif isinstance(item, Image):
                itemFn = item.getFileName()
                # use Location as item representation
                repPath = self.getTopLevelPath(self.DIR_IMAGES,
                                               '%s_%s_%s' % (self.outputName,
                                                             item.getIndex(),
                                                             pwutils.replaceBaseExt(itemFn, 'jpg')))
                self.createThumbnail(itemFn, repPath,
                                     Micrograph if isinstance(item, Micrograph) else Particle if isinstance(item, Particle) else None,
                                     count)
                itemDict[self.ITEM_REPRESENTATION] = repPath

            elif isinstance(item, CTFModel):
                # if exists use ctfmodel_quadrant as item representation, in other case use psdFile
                if item.hasAttribute('_xmipp_ctfmodel_quadrant'):
                    itemPath = str(item._xmipp_ctfmodel_quadrant)
                    repPath = self.getTopLevelPath(self.DIR_IMAGES,
                                                   '%s_%s' % (self.outputName,
                                                              pwutils.replaceBaseExt(itemPath, 'jpg')))

                    self._ih.convert(itemPath, self.getProjectPath(repPath))
                else:
                    itemPath = item.getPsdFile()
                    repPath = self.getTopLevelPath(self.DIR_IMAGES,
                                                   '%s_%s' % (self.outputName,
                                                              pwutils.replaceBaseExt(itemPath, 'jpg')))

                    image = emlib.Image(itemPath)
                    data = image.getData()

                    GAMMA = 2.2 # apply a gamma correction
                    data = data ** (1/GAMMA)
                    data = np.fft.fftshift(data)

                    image.setData(data)
                    image.write(repPath)

                itemDict[self.ITEM_REPRESENTATION] = repPath

            else:
                # in any other case look for a representation on attributes
                for key, value in attributes:
                    itemPath = str(value)
                    if os.path.exists(itemPath):
                        repPath = self.getTopLevelPath(self.DIR_IMAGES,
                                                       '%s_%s' % (self.outputName,
                                                                  pwutils.replaceBaseExt(itemPath, 'png')))
                        self._ih.convert(itemPath, self.getProjectPath(repPath))
                        itemDict[self.ITEM_REPRESENTATION] = repPath
                        break

        except Exception as e:
            self.error(f"Cannot obtain item representation for {str(item)}: {e}")

        return itemDict

    def createThumbnail(self, inputFn, outputFn, type, count=None):
        """ Apply a low pass filter and make a jpg thumbnail. """
        outputFn = self.getProjectPath(outputFn)
        # if inputFn.endswith('.stk'):
        #     self._ih.convert(inputFn, outputFn)
        x, y, z, n = self._ih.getDimensions(inputFn)
        getEnviron = Domain.importFromPlugin('xmipp3', 'Plugin', doRaise=True).getEnviron
        if type == Particle:
            args = f" -i {inputFn if n == 1 else f'{count}@{inputFn}'} -o {outputFn}"
            self.runJob('xmipp_image_convert', args, env=getEnviron())
        elif type == Micrograph:
            args = f" -i {inputFn if n == 1 else f'{count}@{inputFn}'} -o {outputFn} --fourier low_pass 0.05"
            self.runJob('xmipp_transform_filter', args, env=getEnviron())

    def getAdditionalPlots(self, prot):
        """ Generate additional plots apart from basic thumbnails. """
        def getMRCVolume(output, outputName):
            itemFn = output.getFileName()
            if itemFn.endswith('mrc'):
                itemFn = itemFn.replace(':mrc', '')
                repPath = self.getTopLevelPath(self.DIR_IMAGES,
                                               f"{outputName}_{pwutils.removeBaseExt(itemFn)}.mrc")
                shutil.copy(itemFn, repPath)
            if itemFn.endswith('.map'):
                repPath = self.getTopLevelPath(self.DIR_IMAGES,
                                               f"{outputName}_{pwutils.removeBaseExt(itemFn)}.map")
                shutil.copy(itemFn, repPath)
            if itemFn.endswith('.vol'): # already copied (because it was previously converted to mrc)
                repPath = self.getTopLevelPath(self.DIR_IMAGES,
                                               f"{outputName}_{pwutils.removeBaseExt(itemFn)}.mrc")
            return f"{outputName}_{pwutils.removeBaseExt(itemFn)}_3D", repPath

        plotPaths = {}
        for a, output in prot.iterOutputAttributes():
            # alignment methods
            if isinstance(output, SetOfMicrographs):
                shiftsX, shiftsY, totalShifts = [], [], []
                for item in output.iterItems():
                    # XmippProtFlexAlign, XmippProtMovieMaxShift...
                    if item.hasAttribute('_xmipp_ShiftX') and item.hasAttribute('_xmipp_ShiftY'):
                        shiftsX = [float(x) for x in item.getAttributeValue('_xmipp_ShiftX').split(',')]
                        shiftsY = [float(y) for y in item.getAttributeValue('_xmipp_ShiftY').split(',')]

                    # ProtRelionMotioncor
                    elif os.path.exists(os.path.join(prot._getExtraPath(), pwutils.replaceBaseExt(item.getMicName(), 'star'))):
                        starFile = os.path.join(prot._getExtraPath(), pwutils.replaceBaseExt(item.getMicName(), 'star'))
                        table = md.Table(fileName=starFile, tableName='global_shift')

                        for i, row in enumerate(table):
                            shiftsX.append(float(row.rlnMicrographShiftX))
                            shiftsY.append(float(row.rlnMicrographShiftY))

                    if len(shiftsX) > 0 and len(shiftsY) > 0:
                        # relative shifts
                        relativeShiftsX = [shiftsX[i] - shiftsX[i-1] for i in range(1, len(shiftsX))]
                        relativeShiftsY = [shiftsY[i] - shiftsY[i-1] for i in range(1, len(shiftsY))]

                        totalShifts.append(sqrt(sum((x**2 + y**2) for x, y in zip(relativeShiftsX, relativeShiftsY))))

                        numberOfBins = 10
                        plotterShifts = EmPlotter()
                        plotterShifts.createSubPlot("Total shifts histogram", "Drift (pixels)", "#")
                        plotterShifts.plotHist(totalShifts, nbins=numberOfBins)
                        repPath = self.getTopLevelPath(self.DIR_IMAGES, f'{output.getObjName()}_shifts_histogram.jpg')
                        plotterShifts.savefig(os.path.join(self.getProject().path, repPath))
                        plotterShifts.close()
                        plotPaths[f'{output.getObjName()}_shifts_histogram'] = repPath

            # CTF methods
            if isinstance(output, SetOfCTF):
                defocusU = [ctf.getDefocusU() for ctf in output]
                defocusV = [ctf.getDefocusV() for ctf in output]
                defocus = [(defU + defV)/2 for defU, defV in zip(defocusU, defocusV)]
                astigmatism = [abs(defU - defV)/2 for defU, defV in zip(defocusU, defocusV)]

                numberOfBins = 10
                plotterDefocus = EmPlotter()
                plotterAstigmatism = EmPlotter()

                plotterDefocus.createSubPlot("Defocus histogram", "Defocus (A)", "#")
                plotterDefocus.plotHist(defocus, nbins=numberOfBins)
                repPath = self.getTopLevelPath(self.DIR_IMAGES, f'{output.getObjName()}_defocus_histogram.jpg')
                plotterDefocus.savefig(os.path.join(self.getProject().path, repPath))
                plotterDefocus.close()
                plotPaths[f'{output.getObjName()}_defocus_histogram'] = repPath

                plotterAstigmatism.createSubPlot("Astigmatism histogram", "Astigmatism (A)", "#")
                plotterAstigmatism.plotHist(astigmatism, nbins=numberOfBins)
                repPath = self.getTopLevelPath(self.DIR_IMAGES, f'{output.getObjName()}_defocus_astigmatism.jpg')
                plotterAstigmatism.savefig(os.path.join(self.getProject().path, repPath))
                plotterAstigmatism.close()
                plotPaths[f'{output.getObjName()}_defocus_astigmatism.jpg'] = repPath

            # Volumes
            if isinstance(output, Volume):
                name, repPath = getMRCVolume(output, output.getObjName())
                plotPaths[name] = repPath

            elif isinstance(output, SetOfVolumes):
                for item in output.iterItems():
                    name, repPath = getMRCVolume(item, output.getObjName())
                    plotPaths[name] = repPath

        return plotPaths

    def writeSlices(self, V, fnRoot, direction):
        """ Generate volume slices for x, y and z axis. """
        V = np.squeeze(V) # for volumes with numpy arrays with 4 dims
        m = np.min(V)
        M = np.max(V)
        V = (V - m) / (M - m) * 255
        Zdim, Ydim, Xdim = V.shape
        if direction == 'X':
            for j in range(Xdim):
                I = ImagePIL.fromarray(np.reshape(V[:, :, j], [Zdim, Ydim]).astype(np.uint8))
                I.save(f'{fnRoot}_{"{:04d}".format(j)}.jpg')
        if direction == 'Y':
            for i in range(Ydim):
                I = ImagePIL.fromarray(np.reshape(V[:, i, :], [Zdim, Xdim]).astype(np.uint8))
                I.save(f'{fnRoot}_{"{:04d}".format(i)}.jpg')
        if direction == 'Z':
            for k in range(Zdim):
                I = ImagePIL.fromarray(np.reshape(V[k, :, :], [Ydim, Xdim]).astype(np.uint8))
                I.save(f'{fnRoot}_{"{:04d}".format(k)}.jpg')