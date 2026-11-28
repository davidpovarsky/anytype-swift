"""Closed validation of the two new runtime observation HTTP envelopes.

Only scalar public runtime observations are accepted. These checks do not claim
object existence, cloud custody, Personal provenance or a Heart syncDate.
"""
import datetime
import re

STATES = {'unknown', 'offline', 'syncing', 'synced', 'error'}
P2P = {'unknown', 'notpossible', 'notconnected', 'connected', 'restricted'}
SCOPE_KEYS = {'accountId', 'networkId', 'spaceId', 'authorityIdentity', 'aclHeadId'}


def require(value, message):
    if not value:
        raise AssertionError(message)


def fields(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), 'closed runtime field set')
    return value


def text(value, maximum=1024):
    require(isinstance(value, str) and 0 < len(value.encode('utf-8')) <= maximum and '\x00' not in value,
            'bounded exact UTF-8 identity/string')
    return value


def timestamp(value, nullable=False):
    if value is None and nullable:
        return None
    text(value, 64)
    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})', value),
            'native RFC3339Nano timestamp')
    parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None and parsed != datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
            'an observed timestamp is not Go zero time')
    # Keep the original nanoseconds/offset text. Python's parsed microsecond
    # value is used only for calendar validity and never replaces native bytes.
    return value


def unsigned(value, maximum=2**63-1):
    require(type(value) is int and 0 <= value <= maximum, 'nonnegative native integer, never a boolean')
    return value


def scope(value, account, network, space, authority):
    fields(value, SCOPE_KEYS)
    for item in value.values():
        text(item)
    require(value['accountId'] == account and value['networkId'] == network and
            value['spaceId'] == space and value['authorityIdentity'] == authority,
            'exact current account/network/Space/authority observation')
    return dict(value)


def owner_space(value, account, network, space, authority):
    fields(value, {'contract', 'scope', 'capturedAt', 'coordinator', 'access'})
    require(value['contract'] == 'pinkha-space-runtime-state-v1', 'versioned native Space runtime contract')
    observed_scope = scope(value['scope'], account, network, space, authority)
    timestamp(value['capturedAt'])
    coordinator = value['coordinator']
    if coordinator is not None:
        fields(coordinator, {'fetchedAt', 'status', 'isShared', 'limits'})
        timestamp(coordinator['fetchedAt'])
        text(coordinator['status'], 128)
        require(type(coordinator['isShared']) is bool, 'original coordinator sharing boolean')
        if coordinator['limits'] is not None:
            fields(coordinator['limits'], {'readersLimit', 'writersLimit'})
            unsigned(coordinator['limits']['readersLimit'], 2**32-1)
            unsigned(coordinator['limits']['writersLimit'], 2**32-1)
    access = fields(value['access'], {'aclIsEmpty', 'personalSpaceId', 'value', 'reason'})
    require(type(access['aclIsEmpty']) is bool and access['personalSpaceId'] is None and
            access['value'] is None and access['reason'] == 'personal_provenance_unavailable',
            'this exact producer must preserve unavailable Personal provenance and absent classification')
    return observed_scope


def owner_object(value, account, network, space, authority, object_id):
    fields(value, {'contract', 'scope', 'objectId', 'capturedAt', 'objectSync', 'spaceSync'})
    require(value['contract'] == 'pinkha-object-runtime-state-v1' and value['objectId'] == object_id,
            'versioned exact requested native object observation')
    observed_scope = scope(value['scope'], account, network, space, authority)
    timestamp(value['capturedAt'])
    obj = fields(value['objectSync'], {'state', 'basis', 'lastSyncAt'})
    require(obj['state'] in STATES and obj['basis'] in {'per_object_hooks', 'responsible_space_round', 'unobserved'},
            'original SDK sync domain and explicit source provenance')
    timestamp(obj['lastSyncAt'], nullable=True)
    if obj['basis'] == 'unobserved':
        require(obj['state'] == 'unknown' and obj['lastSyncAt'] is None, 'unobserved is unknown with no invented time')
    if obj['basis'] == 'responsible_space_round':
        require(obj['state'] == 'synced' and obj['lastSyncAt'] is not None, 'inherited successful-space-round provenance')
    state = fields(value['spaceSync'], {'spaceId', 'state', 'synced', 'total', 'networkPeers', 'localPeers',
                                      'globalPeers', 'p2p', 'lastSyncedAt', 'networkProtocolIncompatible'})
    require(state['spaceId'] == space and state['state'] in STATES and state['p2p'] in P2P and
            type(state['networkProtocolIncompatible']) is bool, 'original separately observed Space sync domain')
    for name in ('synced', 'total', 'networkPeers', 'localPeers', 'globalPeers'):
        unsigned(state[name])
    require(state['synced'] <= state['total'], 'native synced count cannot exceed observed total')
    timestamp(state['lastSyncedAt'], nullable=True)
    return observed_scope


def denial(value, space, object_id=None):
    fields(value, {'error'})
    error = value['error']
    require(isinstance(error, dict) and {'code', 'message'} <= set(error) <= {'code', 'message', 'details'} and
            error['code'] == 'acl.forbidden' and isinstance(error['message'], str),
            'typed native authority error with no observation envelope')
    details = error.get('details')
    if details is not None:
        require(isinstance(details, dict) and set(details) <= {'spaceId', 'objectId'}, 'scope-only error details')
        if 'spaceId' in details:
            require(details['spaceId'] == space, 'error belongs to the exact requested Space')
        if 'objectId' in details:
            require(object_id is not None and details['objectId'] == object_id, 'error belongs to the exact requested object')
    return {'typedDenial': True}
