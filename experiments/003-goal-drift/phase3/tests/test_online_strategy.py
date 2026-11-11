from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"phase2"/"src")); sys.path.insert(0,str(ROOT/"phase3"/"src"))
import detectors
from online_strategy import build_trace,project_memory

OLD="Topic: work. keep the overall cost as low as possible. finish as quickly as practical."
NEW="Topic: work. quality matters more than price. check every important detail."
PARAMS={"alpha":1.0,"candidate_margin":0.1,"confirmations":2,"window":2,"recovery_votes":1,"timeout":2,"pending_weight":0.4}

def sessions(texts): return [{"session_id":i,"text":x} for i,x in enumerate(texts)]

class OnlineStrategyTests(unittest.TestCase):
    def test_persistent_drift_confirms(self):
        trace=build_trace(sessions([OLD]*3+[NEW,NEW,NEW]),PARAMS,detectors)
        self.assertEqual(trace[3]["state"],"pending")
        self.assertEqual(trace[4]["state"],"confirmed")

    def test_temporary_change_recovers(self):
        trace=build_trace(sessions([OLD]*3+[NEW,NEW,OLD,OLD]),PARAMS,detectors)
        self.assertEqual(trace[4]["state"],"confirmed")
        self.assertEqual(trace[5]["state"],"neutral")
        self.assertEqual(trace[5]["event"],"recovered")

    def test_single_false_candidate_times_out(self):
        p={**PARAMS,"recovery_votes":3}
        trace=build_trace(sessions([OLD]*3+[NEW,OLD,OLD]),p,detectors)
        self.assertEqual(trace[3]["state"],"pending")
        self.assertEqual(trace[5]["state"],"neutral")
        self.assertEqual(trace[5]["event"],"timeout_restore")

    def test_missed_change_does_not_fabricate_update(self):
        trace=build_trace(sessions([OLD]*6),PARAMS,detectors)
        self.assertTrue(all(x["state"]=="neutral" for x in trace))

    def test_background_is_protected(self):
        memories=[{"session_id":0,"kind":"stable_background","key":"background","value":"windows","weight":1.0,"state":"active"},
                  {"session_id":0,"kind":"long_term_goal","key":"cost","value":"economy","weight":1.0,"state":"active"}]
        state={"state":"confirmed","target":("premium","thorough")}
        weights={"temporary_scope_weight":.25,"pending_weight":.4,"confirmed_weight":.1}
        out=project_memory(memories,state,weights)
        self.assertEqual(out[0]["weight"],1.0)
        self.assertEqual(out[1]["weight"],.1)

if __name__=="__main__": unittest.main()
