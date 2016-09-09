
from collections import defaultdict
from oslo_log import log

from cinderclient import client

from playnetmano_rm.common import exceptions
from playnetmano_rm.drivers import base

LOG = log.getLogger(__name__)
API_VERSION = '2'


class CinderClient(base.DriverBase):
    '''Cinder V2 driver.'''

    def __init__(self, region, disabled_quotas, session):
        try:
            self.cinder = client.Client(API_VERSION,
                                        session=session,
                                        region_name=region)
            self.no_volumes = True if 'volumes' in disabled_quotas else False
        except exceptions.ServiceUnavailable:
            raise

    def get_resource_usages(self, project_id):
        '''Calcualte resources usage and return the dict

        :param: project_id
        :return: resource usage dict
        '''
        if not self.no_volumes:
            try:
                usages = defaultdict(dict)

                opts = {'all_tenants': 1, 'project_id': project_id}

                volumes = self.cinder.volumes.list(search_opts=opts)
                snapshots = self.cinder.volume_snapshots.list(search_opts=opts)
                backups = self.cinder.backups.list(search_opts=opts)

                usages['gigabytes'] = sum([int(v.size) for v in volumes])
                usages['volumes'] = len(volumes)
                usages['snapshots'] = len(snapshots)
                usages['backups'] = len(backups)
                return usages

            except exceptions.InternalError:
                raise

    def update_quota_limits(self, project_id, **new_quota):
        '''Update the limits'''
        try:
            if not self.no_volumes:
                return self.cinder.quotas.update(project_id, **new_quota)
        except exceptions.InternalError:
            raise

    def delete_quota_limits(self, project_id):
        '''Delete/Reset the limits'''
        try:
            if not self.no_volumes:
                return self.cinder.quotas.delete(project_id)
        except exceptions.InternalError:
            raise
