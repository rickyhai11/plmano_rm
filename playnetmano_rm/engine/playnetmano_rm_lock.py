from oslo_config import cfg
from oslo_log import log as logging

from playnetmano_rm.common.i18n import _
from playnetmano_rm.common.i18n import _LE
from playnetmano_rm.common.i18n import _LI
from playnetmano_rm.db import api as db_api
from playnetmano_rm.engine import scheduler


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

lock_opts = [
    cfg.IntOpt('lock_retry_times',
               default=3,
               help=_('Number of times trying to grab a lock.')),
    cfg.IntOpt('lock_retry_interval',
               default=10,
               help=_('Number of seconds between lock retries.'))
]

lock_opts_group = cfg.OptGroup('locks')
cfg.CONF.register_group(lock_opts_group)
cfg.CONF.register_opts(lock_opts, group=lock_opts_group)


def sync_lock_acquire(context, engine_id, task_type, forced=False):
    """Try to lock with specified engine_id.

    :param engine: ID of the engine which wants to lock the projects.
    :returns: True if lock is acquired, or False otherwise.
    """

    # Step 1: try lock the projects- if it returns True then success
    LOG.info(_LI('Trying to acquire lock with %(engId)s for Task: %(task)s'),
             {'engId': engine_id,
              'task': task_type
              }
             )
    lock_status = db_api.sync_lock_acquire(context, engine_id, task_type)
    if lock_status:
        return True

    # Step 2: retry using global configuration options
    retries = cfg.CONF.locks.lock_retry_times
    retry_interval = cfg.CONF.locks.lock_retry_interval

    while retries > 0:
        scheduler.sleep(retry_interval)
        LOG.info(_LI('Retry acquire lock with %(engId)s for Task: %(task)s'),
                 {'engId': engine_id,
                  'task': task_type
                  }
                 )
        lock_status = db_api.sync_lock_acquire(context, engine_id, task_type)
        if lock_status:
            return True
        retries = retries - 1

    # Step 3: Last resort is 'forced locking', only needed when retry failed
    if forced:
        lock_status = db_api.sync_lock_steal(context, engine_id, task_type)
        if not lock_status:
            return False
        else:
            return True

    # Will reach here only when not able to acquire locks with retry

    LOG.error(_LE('Not able to acquire lock  for %(task)s with retry'
                  ' with engineId %(engId)s'),
              {'engId': engine_id,
               'task': task_type
               }
              )
    return False


def sync_lock_release(context, engine_id, task_type):
    """Release the lock for the projects"""

    LOG.info(_LI('Releasing acquired lock with %(engId)s for Task: %(task)s'),
             {'engId': engine_id,
              'task': task_type
              }
             )
    return db_api.sync_lock_release(context, task_type)


def list_opts():
    yield lock_opts_group.name, lock_opts
