"""Explicit research-case selection from a larger PROVISIONAL EPM GIS territory.

No customer service connection is certified by these scenario definitions.
The same GIS backbone is retained. Only out-of-scenario modelled household
service branches and demands are excluded. No transformer assignment changes.
"""
from __future__ import annotations

# These are from the 2026-11-03 GitLab houses_candidate_associations.csv
# and are consistent with the 7-, 9- and 12-house *population counts* in
# saved PyPSA manifests. Load profiles remain SYNTHETIC and ordinal, not meters.
CASE_HOUSE_IDS = {
    'seven': ('H03','H06','H26','H27','H28','H34','H35'),
    'nine': ('H01','H02','H03','H06','H26','H27','H28','H34','H35'),
    'twelve': ('H11','H13','H16','H17','H18','H19','H20','H21',
               'H22','H23','H24','H25'),
}
EXPECTED_TRANSFORMER = {'seven':'94022','nine':'94022','twelve':'106039'}
EXCLUDED_PROVISIONAL = {'seven':('H01','H02','H29'),
                        'nine':('H29',), 'twelve':()}


def choose_attachments(case: str, attachments: list, transformer: str):
    """Select an explicit set of attached houses, failing on missing/wrong nodes.

    Does not change source assignments. Caller should remove only the corresponding
    HOUSE_x nodes from a copy of the pandapower-preparation graph.
    """
    if case not in CASE_HOUSE_IDS or transformer != EXPECTED_TRANSFORMER[case]:
        raise ValueError('Case and transformer mismatch')
    ids=CASE_HOUSE_IDS[case]
    by_id={a['house']:a for a in attachments}
    if len(by_id)!=len(attachments):
        raise ValueError('Duplicate household ID in GIS territory')
    missing=sorted(set(ids)-set(by_id))
    if missing:
        raise ValueError(f'{case}: GIS feeder is missing required houses: {missing}. '
                         'Do not invent customer connections.')
    if any(str(by_id[h].get('trafo'))!=transformer for h in ids):
        raise ValueError('GIS attachment transformer mismatch')
    return [by_id[hid] for hid in ids]


def filter_territory(case: str, territory, Territory):
    """Return scenario-specific Territory retaining original GIS LV backbone."""
    tr=str(territory.trafo['identifier'])
    selected=choose_attachments(case,territory.attachments,tr)
    keep={a['house'] for a in selected}
    graph=territory.graph.copy()
    dropped=[a['house'] for a in territory.attachments if a['house'] not in keep]
    for hid in dropped:
        node='HOUSE_'+hid
        if node not in graph:
            raise ValueError('Missing GIS household node '+node)
        graph.remove_node(node)
    if any('HOUSE_'+h not in graph for h in keep):
        raise ValueError('Selected household missing in graph after filtering')
    # Preserve all EPM GIS lines. The unused assumed tapping nodes may remain as
    # harmless degree-two nodes, but the unselected service branches do not.
    return Territory(trafo=territory.trafo,graph=graph,attachments=selected,
                     label=territory.label+';CASE_'+case.upper()+'_SUBSET',
                     root=territory.root,line_count=territory.line_count),dropped
