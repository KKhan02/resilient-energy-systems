import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import geo_screen
import demand_screen

class CatalogChecks(unittest.TestCase):
    def test_catalog_counts(self):
        p=Path(__file__).resolve().parents[1]/"data"/"reference"/"community_catalog_checkin.csv"
        with p.open(newline="",encoding="utf-8") as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),21)
        totals={reg:sum(int(r["survey_respondents"]) for r in rows if r["region"]==reg) for reg in ("Oti","Savannah")}
        self.assertEqual(totals,{"Oti":298,"Savannah":222})

class GeometryTests(unittest.TestCase):
    def test_degree_latitude(self):
        self.assertAlmostEqual(geo_screen.distance_m((0,0),(1,0)),111195.08,delta=100)
    def test_three_house_line(self):
        rows=[{"household_id":k,"latitude":7.,"longitude":lon} for k,lon in (("H1",0.),("H2",.001),("H3",.002))]
        summary,homes,edges=geo_screen.build_screen(rows)
        self.assertEqual(summary["medoid_household_id"],"H2")
        self.assertEqual(len(edges),2)
        self.assertAlmostEqual(summary["straight_line_mst_length_m"],summary["straight_line_star_length_m"],delta=.01)
        self.assertEqual(len(homes),3)
    def test_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"pts.csv"
            p.write_text("household_id,community,latitude,longitude\nH01,Chinekope,7.68,0.06\nH01,Chinekope,7.69,0.07\n")
            with self.assertRaises(ValueError):
                geo_screen.load_households(p,"Chinekope")

class DemandTests(unittest.TestCase):
    def test_appliance_math(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"use.csv"
            p.write_text("household_id,community,appliance,quantity,rated_watts,hours_per_day,days_per_week\nH01,Chinekope,light,2,10,5,7\nH01,Chinekope,radio,1,20,2,7\n")
            rows,s=demand_screen.calculate(p,"Chinekope")
            self.assertEqual(s["households_with_appliance_records"],1)
            self.assertAlmostEqual(rows[0]["average_kwh_per_day"],.14)

if __name__=="__main__":
    unittest.main()
