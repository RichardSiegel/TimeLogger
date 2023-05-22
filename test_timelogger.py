# How to run this test:
# watch "python3 -m unittest test_timelogger.py 2>&1 | grep FAIL"

import unittest
import json
from datetime import datetime

from timelogger import Task
from timelogger import TimeBlock
from timelogger import TimeConflict

today=int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

def todays_timestamp(h,m):
    return datetime.now().replace(hour=h, minute=m, second=0, microsecond=0).timestamp()

class TaskTimeBlock(unittest.TestCase):
    def test_constructor_without_time(self):
        block = TimeBlock()
        self.assertTrue(block.start != None)
        self.assertEqual(block.end,None)
        block = TimeBlock('9-17')
        self.assertEqual(block.start-today,3600*9)
        self.assertEqual(block.end-today,3600*17)
        block = TimeBlock('9-1')
        self.assertEqual(block.start,None)
        self.assertEqual(block.end,None)
        block = TimeBlock('9-now')
        self.assertEqual(block.start-today,3600*9)
        self.assertEqual(block.end,None)
        block = TimeBlock('now-20')
        self.assertEqual(block.start,None)
        self.assertEqual(block.end,None)
        block = TimeBlock('now-now')
        self.assertEqual(block.start,None)
        self.assertEqual(block.end,None)

    def test_to_string(self):
        self.assertTrue(TimeBlock().to_string().endswith('-now'))
        self.assertEqual(TimeBlock('10-23').to_string(),"10:00-23:00")

    def test_representation(self):
        self.assertEqual(f"{TimeBlock('10-23')}","10:00-23:00")
        self.assertEqual(f"{TimeBlock('10:45-23:15')}","10:45-23:15")
        self.assertEqual(f"{TimeBlock('10-now')}","10:00-now")

    def test_constructor_without_end_time(self):
        block = TimeBlock("7-now")
        self.assertEqual(block.start-today, 3600*7)
        self.assertEqual(block.end, None)

    def test_constructor_with_time(self):
        block = TimeBlock("10:00-23:30")
        self.assertEqual(block.start-today, 3600*10)
        self.assertEqual(block.end-today, 3600*23.5)

    def test_string_to_timestamp(self):
        self.assertEqual(TimeBlock.string_to_timestamp(''),None)
        self.assertEqual(TimeBlock.string_to_timestamp('9'),todays_timestamp(9, 0))
        self.assertEqual(TimeBlock.string_to_timestamp('9:00'),todays_timestamp(9, 0))
        self.assertEqual(TimeBlock.string_to_timestamp('8:15'),todays_timestamp(8, 15))
        self.assertEqual(TimeBlock.string_to_timestamp('21:59'),todays_timestamp(21, 59))
        self.assertEqual(TimeBlock.string_to_timestamp('24:00'),None)
        self.assertEqual(TimeBlock.string_to_timestamp('23:60'),None)
        self.assertEqual(TimeBlock.string_to_timestamp('23:050'),None)
        self.assertEqual(TimeBlock.string_to_timestamp('-1'),None)
        self.assertEqual(TimeBlock.string_to_timestamp('0'),todays_timestamp(0, 0))
        self.assertEqual(TimeBlock.string_to_timestamp('23'),todays_timestamp(23, 0))
        self.assertEqual(TimeBlock.string_to_timestamp('24'),None)
        self.assertEqual(TimeBlock.string_to_timestamp('30'),None)

    def test_less_than(self):
        self.assertTrue(TimeBlock('8-9') < TimeBlock('9-10'))

    def test_greater_than(self):
        self.assertTrue(TimeBlock('9-10') > TimeBlock('8-9'))

    def test_stop(self):
        block = TimeBlock()
        self.assertTrue(block.end == None)
        block.stop()
        self.assertTrue(block.end != None)

    def test_find_relation(self):
        block = TimeBlock("10:15-20:15")
        before = TimeBlock("8:15-9:15")
        after = TimeBlock("21:15-23:15")
        touchingBefore = TimeBlock("9:15-10:15")
        touchingAfter = TimeBlock("20:15-21:15")
        within = TimeBlock("11:15-19:15")
        arround = TimeBlock("9:15-21:15")
        intersectStart = TimeBlock("9:15-11:15")
        withinFromStart = TimeBlock("10:15-19:15")
        intersectEnd = TimeBlock("19:15-21:15")
        withinToEnd = TimeBlock("11:15-20:15")
        self.assertEqual(block.whould_be_without(before),TimeConflict.UNCHANGED)
        self.assertEqual(block.whould_be_without(after),TimeConflict.UNCHANGED)
        self.assertEqual(block.whould_be_without(touchingBefore),TimeConflict.UNCHANGED)
        self.assertEqual(block.whould_be_without(touchingAfter),TimeConflict.UNCHANGED)
        self.assertEqual(block.whould_be_without(within),TimeConflict.SPLIT)
        self.assertEqual(block.whould_be_without(arround),TimeConflict.REMOVED)
        self.assertEqual(block.whould_be_without(block),TimeConflict.REMOVED)
        self.assertEqual(block.whould_be_without(intersectStart),TimeConflict.CUTOFF_AT_START)
        self.assertEqual(block.whould_be_without(withinFromStart),TimeConflict.CUTOFF_AT_START)
        self.assertEqual(block.whould_be_without(intersectEnd),TimeConflict.CUTOFF_AT_END)
        self.assertEqual(block.whould_be_without(withinToEnd),TimeConflict.CUTOFF_AT_END)

    def test_without_time_before_end_of(self):
        block = TimeBlock('10-12').without_time_before_end_of(TimeBlock('9-11'))
        self.assertEqual((block.start-today)/3600, 11)
        self.assertEqual((block.end-today)/3600, 12)

    def test_without_time_after_start_of(self):
        block = TimeBlock('10-12').without_time_after_start_of(TimeBlock('11-15'))
        self.assertEqual((block.start-today)/3600, 10)
        self.assertEqual((block.end-today)/3600, 11)

    def test_get_houres(self):
        self.assertEqual(TimeBlock('10-12').get_houres(), 2)
        self.assertEqual(TimeBlock('10:45-12').get_houres(), 1.25)
        self.assertTrue(TimeBlock('0-now').get_houres() > 0)
        self.assertEqual(TimeBlock('now-20').get_houres(), 0)


class TaskTask(unittest.TestCase):
    def setUp(self):
        self.task = Task("Test Task")

    def test_is_active(self):
        self.assertFalse(self.task.is_active())
        self.task.start()
        self.assertTrue(self.task.is_active())
        self.task.stop()
        self.assertFalse(self.task.is_active())

    def test_is_hidden(self):
        self.assertFalse(self.task.is_hidden())
        self.task.name = ".Hidden Task"
        self.assertTrue(self.task.is_hidden())

    def test_start(self):
        self.assertFalse(self.task.is_active())
        self.task.start()
        self.assertTrue(self.task.is_active())

    def test_stop(self):
        self.assertFalse(self.task.is_active())
        self.task.start()
        self.assertTrue(self.task.is_active())
        self.task.stop()
        self.assertFalse(self.task.is_active())

    def test_add_time_block(self):
        self.task.add_time_block("10:00-23:30")
        self.assertEqual(len(self.task.time_blocks), 1)
        time_block = self.task.time_blocks[0]
        self.assertEqual(time_block.start-today, 3600*10)
        self.assertEqual(time_block.end-today, 3600*23.5)

    def test_add_time_block_short_input(self):
        self.task.add_time_block("10-23")
        self.assertEqual(len(self.task.time_blocks), 1)
        time_block = self.task.time_blocks[0]
        self.assertEqual(time_block.start-today, 3600*10)
        self.assertEqual(time_block.end-today, 3600*23)

    def test_add_time_block_end_before_start(self):
        self.task.add_time_block("23:30-10:00")
        self.assertEqual(len(self.task.time_blocks), 0)

    def test_add_time_block_until_now(self):
        self.task.add_time_block("11:11-now")
        self.assertEqual(len(self.task.time_blocks), 1)
        time_block = self.task.time_blocks[0]
        self.assertEqual(time_block.start-today, 3600*11+(3600/60)*11)
        self.assertEqual(time_block.end, None)

    def test_get_total_time_spent(self):
        self.task.add_time_block("10:00-11:00")
        self.task.add_time_block("13:00-14:00")
        self.task.add_time_block("15:00-15:15")
        total_time = self.task.get_total_time_spent()
        self.assertEqual(total_time, 2.25)

    def test_add_time_block_overwrite_existing(self):
        self.task.add_time_block("10:15-12")
        self.assertEqual(self.task.get_total_time_spent(), 1.75)
        self.assertEqual(len(self.task.time_blocks), 1)
        self.task.add_time_block("10:15-12")
        self.assertEqual(self.task.get_total_time_spent(), 1.75)
        self.assertEqual(len(self.task.time_blocks), 1)
        self.task.add_time_block("9-13")
        self.assertEqual(self.task.get_total_time_spent(), 4)
        self.assertEqual(len(self.task.time_blocks), 1)
        self.task.add_time_block("8-9:15")
        self.task.add_time_block("7-8")
        self.assertEqual(self.task.get_total_time_spent(), 6)
        self.assertEqual(len(self.task.time_blocks), 3)
        self.task.add_time_block("12:30-15")
        self.assertEqual(self.task.get_total_time_spent(), 8)
        self.assertEqual(len(self.task.time_blocks), 4)
        self.task.add_time_block("8:30-14:45")
        self.assertEqual(self.task.get_total_time_spent(), 8)
        self.assertEqual(len(self.task.time_blocks), 4)
        self.task.add_time_block("8-9:15")
        self.assertEqual(self.task.get_total_time_spent(), 8)
        self.assertEqual(len(self.task.time_blocks), 4)
        self.task.add_time_block("7:30-14:45")
        self.assertEqual(self.task.get_total_time_spent(), 8)
        self.assertEqual(len(self.task.time_blocks), 3)
        self.task.add_time_block("12-13")
        self.assertEqual(self.task.get_total_time_spent(), 8)
        self.assertEqual(len(self.task.time_blocks), 5)
        self.task.add_time_block("0-20")
        self.assertEqual(self.task.get_total_time_spent(), 20)
        self.assertEqual(len(self.task.time_blocks), 1)
        self.task.add_time_block("17-18")
        self.task.add_time_block("18-20")
        self.assertEqual(self.task.get_total_time_spent(), 20)
        self.assertEqual(len(self.task.time_blocks), 3)

    def test_set_description(self):
        self.task.set_description("Test description")
        self.assertEqual(self.task.description, "Test description")

    def test_merge_with(self):
        task1 = Task("Task 1")
        task1.start()
        task1.stop()
        task2 = Task("Task 2")
        task2.start()
        task2.stop()
        self.task.merge_with(task1)
        self.task.merge_with(task2)
        self.assertEqual(len(self.task.time_blocks), 2)

    def test_merge_with_removing_time_blocks(self):
        manyTasks = Task("ManyTasks")
        self.task.add_time_block("6-7")
        self.task.add_time_block("7-8")
        self.task.add_time_block("8-9")
        intersectingTask = Task("Intersecting Task")
        intersectingTask.add_time_block("6:30-8:30")
        self.task.merge_with(intersectingTask)
        self.assertEqual(self.task.get_total_time_spent(), 3)

    def test_get_json(self):
        self.task.set_description("Test description")
        self.task.add_time_block("10:00-11:00")
        from_1 = today + 3600 * 10
        to_1 = today + 3600 * 11
        self.task.add_time_block("12:00-12:30")
        from_2 = today + 3600 * 12
        to_2 = today + 3600 * 12.5
        expected_json = {
            "name": "Test Task",
            "description": "Test description",
            "time_blocks": [
                {"start": float(from_1), "end": float(to_1)},
                {"start": float(from_2), "end": float(to_2)}
            ]
        }
        self.assertEqual(self.task.get_json(), json.dumps(expected_json))

    def test_load_from_json(self):
        from_1 = today + 3600 * 10
        to_1 = today + 3600 * 11
        from_2 = today + 3600 * 12
        to_2 = today + 3600 * 12.5
        json_str = json.dumps({
            "name": "Test Task",
            "description": "Test description",
            "time_blocks": [
                {"start": float(from_1), "end": float(to_1)},
                {"start": float(from_2), "end": float(to_2)}
            ]
        })
        loaded_task = Task.load_from_json(json_str)
        self.assertEqual(loaded_task.name, "Test Task")
        self.assertEqual(loaded_task.description, "Test description")
        self.assertEqual(len(loaded_task.time_blocks), 2)

if __name__ == '__main__':
    unittest.main()
