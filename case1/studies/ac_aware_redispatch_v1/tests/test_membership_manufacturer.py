from pathlib import Path
import sys
from dataclasses import dataclass
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scenario_membership import choose_attachments,filter_territory,CASE_HOUSE_IDS
from fixed_hardware import physical_soc_floor_usable_kwh

@dataclass
class StubGraph:
    nodeset:set
    def copy(self):return StubGraph(self.nodeset.copy())
    def __contains__(self,key):return key in self.nodeset
    def remove_node(self,key):self.nodeset.remove(key)

@dataclass
class StubTerritory:
    trafo:dict
    graph:StubGraph
    attachments:list
    label:str
    root:str
    line_count:int


def fixture_territory(case):
    trafo='94022' if case in ('seven','nine') else '106039'
    people=CASE_HOUSE_IDS['nine']+('H29',) if trafo=='94022' else CASE_HOUSE_IDS['twelve']
    people=tuple(dict.fromkeys(people))
    att=[dict(house=h,trafo=trafo) for h in people]
    return StubTerritory(dict(identifier=trafo),StubGraph({'N0'} | {'HOUSE_'+h for h in people}),att,'provisional','N0',5)

@pytest.mark.parametrize('case,expected_count,removed', [('seven',7,{'H01','H02','H29'}),('nine',9,{'H29'}),('twelve',12,set())])
def test_exact_household_subset(case,expected_count,removed):
    raw=fixture_territory(case)
    selected,dropped=filter_territory(case,raw,StubTerritory)
    assert len(selected.attachments)==expected_count
    assert set(dropped)==removed
    assert set(a['house'] for a in selected.attachments)==set(CASE_HOUSE_IDS[case])
    assert len(raw.attachments)>=len(selected.attachments) # original never altered
    assert set(raw.graph.nodeset) - set(selected.graph.nodeset)=={'HOUSE_'+h for h in removed}


def test_missing_house_does_not_silently_reassign():
    raw=fixture_territory('seven')
    raw.attachments=[a for a in raw.attachments if a['house']!='H03']
    with pytest.raises(ValueError,match='missing required houses'):
        filter_territory('seven',raw,StubTerritory)


def test_wrong_transformer_rejected():
    with pytest.raises(ValueError,match='Case and transformer mismatch'):
        choose_attachments('twelve',[], '94022')


def test_manufacturer_soc_translation():
    assert physical_soc_floor_usable_kwh(1, .20)==pytest.approx(.229)
    assert physical_soc_floor_usable_kwh(5, .20)==pytest.approx(1.145)
    assert physical_soc_floor_usable_kwh(6, .20)==pytest.approx(1.374)
    assert physical_soc_floor_usable_kwh(8, .20)==pytest.approx(1.832)
    assert physical_soc_floor_usable_kwh(5, .10)==0.
    assert (5*(17.3/4)-physical_soc_floor_usable_kwh(5,.2))==pytest.approx(5*5.12*.8)


def test_invalid_manufacturer_soc():
    with pytest.raises(ValueError):physical_soc_floor_usable_kwh(5,1.)
    with pytest.raises(ValueError):physical_soc_floor_usable_kwh(-1,.2)
