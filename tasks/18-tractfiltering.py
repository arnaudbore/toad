# -*- coding: utf-8 -*-
import os
from core.toad.generictask import GenericTask
from lib import mriutil, util
from lib.images import Images


class TractFiltering(GenericTask):
    def __init__(self, subject):
        GenericTask.__init__(self, subject, 'backup', 'tensorfsl', 'tractquerier', 'qa')
        self.setCleanupBeforeImplement(False)
        self.dirty = True

    def implement(self):

        mriutil.setWorkingDirTractometry(self.workingDir,
                                         self.getTractQuerierImages('dwi', None, 'trk'),
                                         [(self.getTensorFSLImage('dwi', 'fa'),'fsl_fa.nii.gz')])

        configFile = self.__getConfigFile('configTractFiltering', 'configTractFiltering_default')

        mriutil.runTractometry(configFile, self.workingDir, self.workingDir)

    def isIgnore(self):
        return self.get("ignore")

    def meetRequirement(self):
        """Validate if all requirements have been met prior to launch the task
        Returns:
            True if all requirement are meet, False otherwise
        """

        #images = Images()

        #Images((self.getTractQuerierImage(None, None, 'trk'),'Tractography files'))

        return True

    def isDirty(self):
        """Validate if this tasks need to be submit during the execution
        Returns:
            True if any expected file or resource is missing, False otherwise
        """
        target_queries = self.getBackupImage('queries', None, 'qry')
        target_dict = self.getBackupImage('tq_dict', None, 'qry')

        outDir = 'raw/outlier_cleaned_tracts'

        if not target_queries and not target_dict:

            return Images((self.getImage('dwi', 'corpus_callosum', 'trk', outDir),'CC'),
                           (self.getImage('dwi', 'cortico_spinal.left', 'trk', outDir),'CS_left'),
                           (self.getImage('dwi', 'cortico_spinal.right', 'trk', outDir),'CS_right'),
                           (self.getImage('dwi', 'inferior_fronto_occipital.left', 'trk', outDir),'IFO_left'),
                           (self.getImage('dwi', 'inferior_fronto_occipital.right', 'trk', outDir),'IFO_right'),
                           (self.getImage('dwi', 'inferior_longitudinal_fasciculus.left', 'trk', outDir),'ILF_left'),
                           (self.getImage('dwi', 'inferior_longitudinal_fasciculus.right', 'trk', outDir),'ILF_right'),
                           (self.getImage('dwi', 'uncinate_fasciculus.left', 'trk', outDir),'UF_left'),
                           (self.getImage('dwi', 'uncinate_fasciculus.right', 'trk', outDir),'UH_right'))
        else:
            outDir = os.path.join(self.workingDir + outDir)
            return os.path.exists(outDir)

    def __getConfigFile(self, prefix, defaultFile):

        target = self.getBackupImage(prefix, None, 'json')
        if target:
            util.symlink(target, self.buildName(target, None, 'json'))
        else:
            defaultFileName = '{}.json'.format(defaultFile)
            defaultFileLink = os.path.join(
                self.toadDir,
                "templates",
                "tractometry",
                defaultFileName,
            )
            target = defaultFileLink
            util.copy(defaultFileLink, self.workingDir, defaultFileName)
            self.defaultQuery = True
        return target


#    def qaSupplier(self):
#        """Create and supply images for the report generated by qa task

#        """
#        qaImages = Images()

#       information = "Warning: due to storage restriction, streamlines were " \
#                      "downsampled. Even if there is no difference in structural " \
#                      "connectivity, you should be careful before computing any " \
#                      "metrics along these streamlines.\n To run toad without this " \
#                      "downsampling, please refer to the documentation."
#        qaImages.setInformation(information)


#        return qaImages
