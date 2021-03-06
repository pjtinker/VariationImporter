# -*- coding: utf-8 -*-
import unittest
import os  # noqa: F401
import json  # noqa: F401
import time
import requests
import shutil
import uuid

from os import environ
try:
    from ConfigParser import ConfigParser  # py2
except:
    from configparser import ConfigParser  # py3

from pprint import pprint  # noqa: F401
from mock import patch

from DataFileUtil.DataFileUtilClient import DataFileUtil
from biokbase.workspace.client import Workspace as workspaceService
from VariationImporter.VariationImporterImpl import VariationImporter
from VariationImporter.VariationImporterServer import MethodContext
from VariationImporter.authclient import KBaseAuth as _KBaseAuth


class VariationImporterTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = environ.get('KB_AUTH_TOKEN', None)
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('VariationImporter'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'VariationImporter',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = workspaceService(cls.wsURL)
        cls.serviceImpl = VariationImporter(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsName(self):
        if hasattr(self.__class__, 'wsName'):
            return self.__class__.wsName
        suffix = int(time.time() * 1000)
        wsName = "test_VariationImporter_" + str(suffix)
        ret = self.getWsClient().create_workspace({'workspace': wsName})  # noqa
        self.__class__.wsName = wsName
        return wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    @staticmethod
    def fake_staging_download(params):
        scratch = '/kb/module/work/tmp/'
        inpath = params['staging_file_subdir_path']
        shutil.copy('/kb/module/data/'+inpath, scratch+inpath)
        return {'copy_file_path': scratch+inpath}

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    @patch.object(DataFileUtil, "download_staging_file",
                  new=fake_staging_download)

    def _save_to_ws_and_report(self, ws_id, source, assembly_data):
        dfu = DataFileUtil(os.environ['SDK_CALLBACK_URL'])
        workspace_id = dfu.ws_name_to_id(self.getWsName())
        print("Workspace id: {}".format(workspace_id))
        info = dfu.save_objects(
            {
                'id': '18590', # Numerical id of workspace
                "objects": [{
                    "type": "KBaseGenomeAnnotations.Assembly-3.0",
                    "data": assembly_data,
                    "name": ws_id
                }]
            })[0]
        #print("Data from save to ws: {}".format(json.dumps(info, indent=2)))
        assembly_ref = "%s/%s/%s" % (info[6], info[0], info[4])

        return assembly_ref

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    def test_your_method(self):
        # Prepare test objects in workspace if needed using
        # self.getWsClient().save_objects({'workspace': self.getWsName(),
        #                                  'objects': []})
        #
        # Run your method by
        # ret = self.getImpl().your_method(self.getContext(), parameters...)
        #
        # Check returned data with
        # self.assertEqual(ret[...], ...) or other unittest methods
        params = {
            'workspace_name' : self.getWsName(),
            'genome_ref' : '18590/2/8',
            'staging_file_subdir_path' : 'test_with_chr.vcf',
            'location_file_subdir_path' : 'population_locality.txt',
            'additional_output_type' : 'plink19'
        }
        
        ret = self.getImpl().import_variation(self.getContext(), params)[0]
        self.assertIsNotNone(ret['report_ref'], ret['report_name'])
        pass
