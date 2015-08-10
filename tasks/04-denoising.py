import os

import dipy.denoise.noise_estimate
import dipy.denoise.nlmeans
import nibabel
import numpy

from core.generictask import GenericTask
from lib.images import Images
from lib import util


__author__ = 'desmat'

class Denoising(GenericTask):


    def __init__(self, subject):
        GenericTask.__init__(self, subject, 'eddy', 'preparation', 'parcellation', 'fieldmap', 'qa')


    def implement(self):
        if self.get("algorithm").lower() in "none":
            self.info("Skipping denoising process")

        else:
            dwi = self.__getDwiImage()
            target = self.buildName(dwi, "denoise")
            if self.get("algorithm") == "nlmeans":

                dwiImage = nibabel.load(dwi)
                dwiData  = dwiImage.get_data()

                try:
                    numberArrayCoil = int(self.get("number_array_coil"))
                except ValueError:
                    numberArrayCoil = 1
                sigmaMatrix = numpy.zeros_like(dwiData, dtype=numpy.float32)
		sigmaVector = numpy.zeros(dwiData.shape[2], dtype=numpy.float32)
                maskNoise = numpy.zeros(dwiData.shape[:-1], dtype=numpy.bool)


                for idx in range(dwiData.shape[2]):
                    sigmaMatrix[:, :, idx], maskNoise[:, :, idx] = dipy.denoise.noise_estimate.piesno(dwiData[:, :, idx],
                                                                                                 N=numberArrayCoil,
                                                                                                 return_mask=True)
                    print "sigma moi le sac=", sigmaMatrix[0,0,idx,0]
                    sigmaVector[idx] = sigmaMatrix[0,0,idx,0]
                sigma = numpy.median(sigmaVector)
                self.info("sigma value that will be apply into nlmeans = {}".format(sigma))
                #denoisingData = dipy.denoise.nlmeans.nlmeans(dwiData, sigma, maskNoise)
		denoisingData = dipy.denoise.nlmeans.nlmeans(dwiData, sigma)
                nibabel.save(nibabel.Nifti1Image(denoisingData.astype(numpy.float32), dwiImage.get_affine()), target)
                nibabel.save(nibabel.Nifti1Image(maskNoise.astype(numpy.float32),
                                                 dwiImage.get_affine()), self.buildName(target, "noise_mask"))

            elif self.get('general', 'matlab_available'):
                dwi = self.__getDwiImage()
                dwiUncompress = self.uncompressImage(dwi)

                tmp = self.buildName(dwiUncompress, "tmp", 'nii')
                scriptName = self.__createMatlabScript(dwiUncompress, tmp)
                self.__launchMatlabExecution(scriptName)

                self.info("compressing {} image".format(tmp))
                tmpCompress = util.gzip(tmp)
                self.rename(tmpCompress, target)

                if self.get("cleanup"):
                    self.info("Removing redundant image {}".format(dwiUncompress))
                    os.remove(dwiUncompress)
            else:
                #@TODO send an error message to QA report
                self.warning("Algorithm {} is set but matlab is not available for this server.\n"
                             "Please configure matlab or set denoising algorithm to nlmeans or none"
                             .format(self.get("algorithm")))


            #QA
            #workingDirDwi = self.getImage(self.workingDir, 'dwi', 'denoise')

            #@TODO b0 brain mask from eddy tasks do not exists anymore
            #if 0:
            #if workingDirDwi:
                #@TODO  remove comments --add a method to get the correct mask
                #mask = os.path.join(self.dependDir, 'topup_results_image_tmean_brain.nii.gz')
                #mask = self.getImage(self.dependDir, 'b0', 'brain')
                #dwiCompareGif = self.buildName(workingDirDwi, 'compare', 'gif')
                #dwiGif = self.buildName(workingDirDwi, None, 'gif')

                #self.slicerGifCompare(dwi, workingDirDwi, dwiCompareGif, boundaries=mask)
                #self.slicerGif(workingDirDwi, dwiGif, boundaries=mask)


    def __getDwiImage(self):
        if self.getImage(self.fieldmapDir, "dwi", 'unwarp'):
            return self.getImage(self.fieldmapDir, "dwi", 'unwarp')
        elif self.getImage(self.dependDir, "dwi", 'eddy'):
            return self.getImage(self.dependDir, "dwi", 'eddy')
        else:
            return self.getImage(self.preparationDir, "dwi")


    def __createMatlabScript(self, source, target):

        scriptName = os.path.join(self.workingDir, "{}.m".format(self.get("script_name")))
        self.info("Creating denoising script {}".format(scriptName))
        tags={ 'source': source,
               'target': target,
               'workingDir': self.workingDir,
               'beta': self.get('beta'),
               'rician': self.get('rician'),
               'nbthreads': self.getNTreadsDenoise()}

        if self.get("algorithm") == "aonlm":
            template = self.parseTemplate(tags, os.path.join(self.toadDir, "templates", "files", "denoise_aonlm.tpl"))
        else:
            template = self.parseTemplate(tags, os.path.join(self.toadDir, "templates", "files", "denoise_lpca.tpl"))

        util.createScript(scriptName, template)
        return scriptName


    def __launchMatlabExecution(self, pyscript):

        self.info("Launch DWIDenoisingLPCA from matlab.")
        self.launchMatlabCommand(pyscript, None, None, 10800)


    def isIgnore(self):
        return (self.get("algorithm").lower() in "none") or (self.get("ignore"))


    def meetRequirement(self, result = True):
        images = Images((self.getImage(self.fieldmapDir, "dwi", 'unwarp'), 'fieldmap'),
                       (self.getImage(self.dependDir, "dwi", 'eddy'), 'eddy corrected'),
                       (self.getImage(self.preparationDir, "dwi"), 'diffusion weighted'))

        #@TODO add those image as requierement
        #norm = self.getImage(self.parcellationDir, 'norm')
        #noiseMask = self.getImage(self.parcellationDir, 'noise_mask')
        if images.isNoImagesExists():
            result = False
            self.warning("No suitable dwi image found for denoising task")
        return result


    def isDirty(self):
        image = Images((self.getImage(self.workingDir, "dwi", 'denoise'), 'denoised'),
                       (self.getImage(self.workingDir, "noise_mask", 'denoise'), 'denoised'))
	print image
        return image.isSomeImagesMissing()


    #def qaSupplier(self):
    #    denoiseGif = self.getImage(self.workingDir, 'dwi', 'denoise', ext='gif')
    #    compareGif = self.getImage(self.workingDir, 'dwi', 'compare', ext='gif')

    #    images = Images((denoiseGif,'Denoised diffusion image'),
    #                    (compareGif,'Before and after denoising'),
    #                   )
    #    images.setInformation(self.get("algorithm"))

    #    return images


"""

if not self.get("eddy", "ignore"):
    bVals= self.getImage(self.eddyDir, 'grad',  None, 'bvals')
else:
    bVals=  self.getImage(self.preparationDir, 'grad',  None, 'bvals')

#create a suitable mask the same space than the dwi
extraArgs = ""
if self.get("parcellation", "intrasubject"):
    extraArgs += " -usesqform  -dof 6"

#extract b0 image from the dwi
b0Image = os.path.join(self.workingDir,
                       os.path.basename(dwi).replace(self.get("prefix", 'dwi'),
                       self.get("prefix", 'b0')))
self.info(mriutil.extractFirstB0FromDwi(dwi, b0Image, bVals))

norm = self.getImage(self.parcellationDir, 'norm')
noiseMask = self.getImage(self.parcellationDir, 'noise_mask')

dwiNoiseMask = mriutil.computeDwiMaskFromFreesurfer(b0Image,
                                            norm,
                                            noiseMask,
                                            self.buildName(noiseMask, 'denoise'),
                                            extraArgs)


dwiNoiseMaskImage = nibabel.load(dwiNoiseMask)
dwiMaskData = dwiNoiseMaskImage.get_data()
sigma = dipy.denoise.noise_estimate.estimate_sigma(dwiData)
self.info("Estimate sigma values = {}".format(sigma))


sigma, mask = dipy.denoise.noise_estimate.piesno(data, N=1, return_mask=True)
alpha=0.01, l=100, itermax=100, eps=1e-5, return_mask=False
"""

