import unittest
from check_saved_frame import field_results

class SavedFrameTests(unittest.TestCase):
    def test_separate_missing_and_incorrect(self):
        expected={'board_slots':['4h','2s','5d',None,None],'amounts':{'right':106550,'upper_right':450},'turn':'upper_right'}
        result={'board_slots':[{'candidate':'4h'},{'candidate':'2s'},{'candidate':None},None,None],'number_candidates':{'right':{'candidate':{'value':186550}},'upper_right':{}},'table_observation':{'turn_candidate':'upper_left'}}
        self.assertEqual([x['status'] for x in field_results(result,expected)],['match','match','missing','match','match','incorrect','missing','incorrect'])
    def test_unreadable_not_empty(self):
        self.assertEqual(field_results({'board_slots':[{'candidate':None}]},{'board_slots':[None]})[0]['status'],'incorrect')
    def test_missing_slots_cannot_pass_as_empty(self):
        for result in ({},{"board_slots":[]},{"board_slots":None}):
            self.assertEqual(field_results(result,{"board_slots":[None]})[0]["status"],"missing")
        self.assertEqual(field_results({"board_slots":[{}]},{"board_slots":[None]})[0]["status"],"incorrect")
    def test_bet_distinct_from_stack(self):
        result={"table_observation":{"seats":{"hero":{"bet":{"value":50},"stack":{"value":19950}}}}}
        self.assertEqual(field_results(result,{"bets":{"hero":50}})[0]["status"],"match")
    def test_zero_not_missing(self):
        self.assertEqual(field_results({'number_candidates':{'left':{'candidate':{'value':0}}}},{'amounts':{'left':0}})[0]['status'],'match')

    def test_malformed_amount_is_not_zero_or_one(self):
        for v in (False,True,0.0,1.0,"0",-1,2**53):
            self.assertEqual(field_results({"number_candidates":{"hero":{"candidate":{"value":v}}}},{"amounts":{"hero":0}})[0]["status"],"missing")
    def test_unknown_marker_is_not_confirmed_absence(self):
        self.assertEqual(field_results({},{"turn":None})[0]["status"],"missing")

if __name__=="__main__":
    unittest.main()
