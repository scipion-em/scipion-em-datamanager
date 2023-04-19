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
from pwem.objects import Class2D, Class3D, Image, CTFModel, Volume, Micrograph, Movie, Particle, SetOfCoordinates
from pyworkflow.protocol import params
from pyworkflow.object import String, Set
import pyworkflow.utils as pwutils
from pyworkflow.project import config
from PIL import Image as ImagePIL
from PIL import ImageDraw
from zipfile import ZipFile, ZIP_DEFLATED
import requests

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
                      help='You can generate an API Token after registering at http://nolan.cnb.csic.es/cryoemworkflowviewer/')
        form.addParam('update', params.BooleanParam, label='Update existing entry?', default=False,
                      help='Is this an update of a previous deposition?')
        form.addParam('entryid', params.StringParam, label='Entry ID to update', condition='update',
                      help='Specify the ID of the existing entry you want to update. If you do not remember it, check it at http://nolan.cnb.csic.es/cryoemworkflowviewer/profile')
        form.addParam('entrytitle', params.StringParam, label='Entry title',
                      help='Specify a descriptive entry title')
        form.addParam('public', params.BooleanParam, label='Make entry public?', default=False,
                      help='Do you want the entry be publicly visible at http://nolan.cnb.csic.es/cryoemworkflowviewer/entries ?')

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
        url = 'https://nolan.cnb.csic.es/cryoemworkflowviewer/uploaddata/%s/%s/%s%s' % (self.apitoken, '1' if self.public else '0', self.entrytitle, '/' + str(self.entryid) if self.update else '')
        response = requests.post(url, files={'workflow': ('workflow.json', workflow), 'thumbnails': ('images_representation.zip', thumbnails)}, verify=False)

        self.response.set(str(response.text))
        self._store()
        print(self.response)

        if response.status_code != 201:
            raise Exception('The submission was not ok: %s' % self.response)

    # --------------- INFO functions -------------------------

    def _validate(self):
        errors = []
        if self.apitoken == '':
            errors.append('You have to provide an API Token (yo can get one at http://nolan.cnb.csic.es/cryoemworkflowviewer/profile )')
        if self.entrytitle == '':
            errors.append('You have to provide a title for the entry')
        if self.update and self.entryid == '':
            errors.append('You have to provide the ID of the entry you want to update. If you do not remember it, check it at http://nolan.cnb.csic.es/cryoemworkflowviewer/profile')
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

    def exportWorkflow(self):
        project = self.getProject()
        workflowProts = [p for p in project.getRuns()]

        for step in workflowProts:
            if self._label in step.__dict__['_objLabel']:
                workflowProts.remove(step)

        workflowJsonPath = self._getExtraPath(self.OUTPUT_WORKFLOW)
        protDicts = project.getProtocolsDict(workflowProts)

        # labels and colors
        settingsPath = os.path.join(project.path, project.settingsPath)
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
            # Get summary and add input and output information
            summary = prot.summary()
            for a, input in prot.iterInputAttributes():
                if input.isPointer():
                    try:
                        inputLabel = ' (from %s) ' % protDicts[int(input.getUniqueId().split('.')[0])]['object.label']
                    except:
                        inputLabel = ''
                summary.append('Input: %s%s- %s\n' % (input.getUniqueId() if input.isPointer() else input.getObjName(), inputLabel, str(input.get())))

            protDicts[prot.getObjId()]['output'] = []
            num = 0
            for a, output in prot.iterOutputAttributes():
                print('output key is %s' % a)
                protDicts[prot.getObjId()]['output'].append(self.getOutputDict(output))
                summary.append('Output: %s - %s\n' % (output.getObjName(), str(output)))

            protDicts[prot.getObjId()]['summary'] = ''.join(summary)

            # Get log (stdout)
            outputs = []
            logs = list(prot.getLogPaths())
            if pwutils.exists(logs[0]):
                logPath = self._getExtraPath(self.DIR_IMAGES, '%s_%s.log' % (prot.getObjId(), prot.getClassName()))
                pwutils.copyFile(logs[0], logPath)
                outputs = logPath

            protDicts[prot.getObjId()]['log'] =  outputs

            # labels
            if prot.getObjId() in protsLabelsDict.keys():
                protDicts[prot.getObjId()]['label'] = protsLabelsDict[prot.getObjId()]
                protDicts[prot.getObjId()]['labelColor'] = []
                for label in protDicts[prot.getObjId()]['label']:
                    protDicts[prot.getObjId()]['labelColor'].append(labelsDict[label])

            # Get plugin and binary version
            protDicts[prot.getObjId()]['plugin'] = prot.getClassPackageName()
            if len(outputs) > 0:
                with open(logPath) as log:
                    for line in log:
                        if re.search(r'plugin v', line):
                            version = line.split(':')[1].replace(' ', '').replace('\n', '')
                            protDicts[prot.getObjId()]['pluginVersion'] = version

        with open(workflowJsonPath, 'w') as f:
            f.write(json.dumps(list(protDicts.values()), indent=4, separators=(',', ': ')))

    # --------------- imageSet utils -------------------------

    def getOutputDict(self, output):
        self.outputName = output.getObjName()
        outputDict = {}
        outputDict[self.OUTPUT_NAME] = output.getObjName()
        outputDict[self.OUTPUT_TYPE] = output.getClassName()

        items = []

        # If output is a Set get a list with all items
        if isinstance(output, Set):
            outputDict[self.OUTPUT_SIZE] = output.getSize()
            count = 0
            if isinstance(output, SetOfCoordinates):
                coordinatesDict = {}
                for micrograph in output.getMicrographs(): # get the first three micrographs
                    count += 1
                    # apply a low pass filter
                    args = ' -i %s -o %s --fourier low_pass %f' % (micrograph.getLocation()[1], self._getTmpPath(os.path.basename(micrograph.getFileName())), 0.05)
                    getEnviron = Domain.importFromPlugin('xmipp3', 'Plugin', doRaise=True).getEnviron
                    self.runJob('xmipp_transform_filter', args, env=getEnviron())
                    # save jpg
                    repPath = self._getExtraPath(self.DIR_IMAGES, '%s_%s' % (self.outputName, pwutils.replaceBaseExt(micrograph.getFileName(), 'jpg')))
                    self._ih.convert(self._getTmpPath(os.path.basename(micrograph.getFileName())), repPath)
                    coordinatesDict[micrograph.getMicName()] = {'path': repPath, 'Xdim': micrograph.getXDim(), 'Ydim': micrograph.getYDim()}

                    items.append({self.ITEM_REPRESENTATION: repPath})
                    if count == 3: break;

                for coordinate in output: # for each micrograph, get its coordinates
                    if coordinate.getMicName() in coordinatesDict:
                        coordinatesDict[coordinate.getMicName()].setdefault('coords', []).append([coordinate.getX(), coordinate.getY()])

                for micrograph, values in coordinatesDict.items(): # draw coordinates in micrographs jpgs
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
                    itemDict = self.getItemDict(item)
                    items.append(itemDict)
                    count += 1
                    # In some types get only a limited number of items
                    if (isinstance(item, Micrograph) or isinstance(item, Movie) or isinstance(item, CTFModel)) and count == 3: break;
                    if isinstance(item, Particle) and count == 15: break;

        # If it is a single object then only one item is present
        else:
            items.append(self.getItemDict(output))

        outputDict[self.OUTPUT_ITEMS] = items

        return outputDict

    def getItemDict(self, item):
        itemDict = {}
        attributes = item.getAttributes()
        for key, value in attributes:
            # Skip attributes that are Pointer
            if not value.isPointer():
                itemDict[key] = str(value)

        itemDict[self.ITEM_ID] = item.getObjId()

        try:
            # Get item representation
            if isinstance(item, Class2D):
                # use representative as item representation
                repPath = self._getExtraPath(self.DIR_IMAGES, '%s_%s_%s' % (self.outputName, item.getRepresentative().getIndex(), pwutils.replaceBaseExt(item.getRepresentative().getFileName(), 'jpg')))
                itemPath = item.getRepresentative().getLocation()
                self._ih.convert(itemPath, repPath)

                if '_size' in itemDict:  # write number of particles over the class
                    text = itemDict['_size'] + ' ptcls'
                    image = ImagePIL.open(repPath).convert('RGB')
                    W, H = image.size
                    draw = ImageDraw.Draw(image)
                    draw.text((5, H - 15), text, fill=(0, 255, 0))
                    image.save(repPath, quality=95)

                itemDict[self.ITEM_REPRESENTATION] = repPath

            elif isinstance(item, Class3D):
                # Get all slices in x,y and z directions of representative to represent the class
                repDir = self._getExtraPath(self.DIR_IMAGES, '%s_%s' % (self.outputName, pwutils.removeBaseExt(item.getRepresentative().getFileName())))
                pwutils.makePath(repDir)
                if item.getFileName().endswith('.mrc'):
                    item.setFileName(item.getFileName() + ':mrc')
                I = emlib.Image(item.getRepresentative().getFileName())
                I.writeSlices(os.path.join(repDir, 'slicesX'), 'jpg', 'X')
                I.writeSlices(os.path.join(repDir, 'slicesY'), 'jpg', 'Y')
                I.writeSlices(os.path.join(repDir, 'slicesZ'), 'jpg', 'Z')

                if '_size' in itemDict: # write number of particles over a class image
                    text = itemDict['_size'] + ' ptcls'
                    image = ImagePIL.open(os.path.join(repDir, 'slicesX_0000.jpg')).convert('RGB')
                    W, H = image.size
                    draw = ImageDraw.Draw(image)
                    draw.text((5, H - 15), text, fill=(0, 255, 0))
                    image.save(os.path.join(repDir, 'slicesX_0000.jpg'), quality=95)

                itemDict[self.ITEM_REPRESENTATION] = repDir

            elif isinstance(item, Volume):
                # Get all slices in x,y and z directions to represent the volume
                repDir = self._getExtraPath(self.DIR_IMAGES, '%s_%s' % (self.outputName, pwutils.removeBaseExt(item.getFileName())))
                pwutils.makePath(repDir)
                if item.getFileName().endswith('.mrc'):
                    item.setFileName(item.getFileName() + ':mrc')
                I = emlib.Image(item.getFileName())
                I.writeSlices(os.path.join(repDir,'slicesX'), 'jpg', 'X')
                I.writeSlices(os.path.join(repDir, 'slicesY'), 'jpg', 'Y')
                I.writeSlices(os.path.join(repDir, 'slicesZ'), 'jpg', 'Z')

                itemDict[self.ITEM_REPRESENTATION] = repDir

            elif isinstance(item, Image):
                # use Location as item representation
                repPath = self._getExtraPath(self.DIR_IMAGES, '%s_%s_%s' % (self.outputName, item.getIndex(), pwutils.replaceBaseExt(item.getFileName(), 'jpg')))
                itemPath = item.getLocation()
                # apply a low pass filter
                if item.getFileName().endswith('.stk'):
                    self._ih.convert(itemPath[1], repPath)
                else:
                    args = ' -i %s -o %s --fourier low_pass %f' % (itemPath[1], self._getTmpPath(os.path.basename(item.getFileName())), 0.05)
                    getEnviron = Domain.importFromPlugin('xmipp3', 'Plugin', doRaise=True).getEnviron
                    self.runJob('xmipp_transform_filter', args, env=getEnviron())
                    self._ih.convert(self._getTmpPath(os.path.basename(item.getFileName())), repPath)
                itemDict[self.ITEM_REPRESENTATION] = repPath

            elif isinstance(item, CTFModel):
                # if exists use ctfmodel_quadrant as item representation, in other case use psdFile
                if item.hasAttribute('_xmipp_ctfmodel_quadrant'):
                    repPath = self._getExtraPath(self.DIR_IMAGES, '%s_%s' % (self.outputName, pwutils.replaceBaseExt(str(item._xmipp_ctfmodel_quadrant), 'jpg')))
                    itemPath = str(item._xmipp_ctfmodel_quadrant)

                else:
                    repPath = self._getExtraPath(self.DIR_IMAGES, '%s_%s' % (self.outputName, pwutils.replaceBaseExt(item.getPsdFile(), 'jpg')))
                    itemPath = item.getPsdFile()

                self._ih.convert(itemPath, repPath)
                itemDict[self.ITEM_REPRESENTATION] = repPath

            else:
                # in any other case look for a representation on attributes
                for key, value in attributes:
                    if os.path.exists(str(value)):
                        repPath = self._getExtraPath(self.DIR_IMAGES, '%s_%s' % (self.outputName, pwutils.replaceBaseExt(str(value), 'png')))
                        itemPath = str(value)
                        self._ih.convert(itemPath, repPath)
                        itemDict[self.ITEM_REPRESENTATION] = repPath
                        break

        except Exception as e:
            print('Cannot obtain item representation for %s' % str(item))

        return itemDict