# How to run this test:
# watch "python3 -m unittest test_timelogger.py"

import unittest
import json
from datetime import datetime
import re

from timelogger import AutoCompleter
from timelogger import Task
from timelogger import TimeBlock
from timelogger import TimeConflict
from timelogger import TimeLogger


def todays_datetime(h,m):
    return datetime.fromtimestamp(1688032800.0).replace(hour=h, minute=m, second=0, microsecond=0)

def todays_timestamp(h,m):
    return datetime.fromtimestamp(1688032800.0).replace(hour=h, minute=m, second=0, microsecond=0).timestamp()

today_datetime=todays_datetime(0,0)
today=todays_timestamp(0,0)

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

    def test_is_valid_range(self):
        self.assertTrue(TimeBlock.is_valid_range("2-5"))
        self.assertTrue(TimeBlock.is_valid_range("2:30-23:59"))
        self.assertFalse(TimeBlock.is_valid_range("2-23:60"))
        self.assertFalse(TimeBlock.is_valid_range("-2-5"))
        self.assertFalse(TimeBlock.is_valid_range("2-24"))
        self.assertFalse(TimeBlock.is_valid_range("-"))
        self.assertFalse(TimeBlock.is_valid_range("now"))
        self.assertFalse(TimeBlock.is_valid_range("10:30"))
        self.assertFalse(TimeBlock.is_valid_range(""))

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

    def test_contains_moment(self):
        self.assertTrue(TimeBlock('9-10').contains_moment(TimeBlock('9:30-now').start))
        self.assertFalse(TimeBlock('9:30-10').contains_moment(TimeBlock('9:30-now').start))
        self.assertFalse(TimeBlock('8-9:30').contains_moment(TimeBlock('9:30-now').start))
        self.assertTrue(TimeBlock('8-now').contains_moment(TimeBlock('9:30-now').start))

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
        self.assertEqual(block.would_be_without(before),TimeConflict.UNCHANGED)
        self.assertEqual(block.would_be_without(after),TimeConflict.UNCHANGED)
        self.assertEqual(block.would_be_without(touchingBefore),TimeConflict.UNCHANGED)
        self.assertEqual(block.would_be_without(touchingAfter),TimeConflict.UNCHANGED)
        self.assertEqual(block.would_be_without(within),TimeConflict.SPLIT)
        self.assertEqual(block.would_be_without(arround),TimeConflict.REMOVED)
        self.assertEqual(block.would_be_without(block),TimeConflict.REMOVED)
        self.assertEqual(block.would_be_without(intersectStart),TimeConflict.CUTOFF_AT_START)
        self.assertEqual(block.would_be_without(withinFromStart),TimeConflict.CUTOFF_AT_START)
        self.assertEqual(block.would_be_without(intersectEnd),TimeConflict.CUTOFF_AT_END)
        self.assertEqual(block.would_be_without(withinToEnd),TimeConflict.CUTOFF_AT_END)

    def test_without_time_before_end_of(self):
        block = TimeBlock('10-12').without_time_before_end_of(TimeBlock('9-11'))
        self.assertEqual((block.start-today)/3600, 11)
        self.assertEqual((block.end-today)/3600, 12)

    def test_without_time_after_start_of(self):
        block = TimeBlock('10-12').without_time_after_start_of(TimeBlock('11-15'))
        self.assertEqual((block.start-today)/3600, 10)
        self.assertEqual((block.end-today)/3600, 11)

    def test_time_spent(self):
        self.assertEqual(TimeBlock('10-12').time_spent(), 2)
        self.assertEqual(TimeBlock('10:45-12').time_spent(), 1.25)
        self.assertTrue(TimeBlock('0-now').time_spent() > 0)
        self.assertEqual(TimeBlock('now-20').time_spent(), 0)


class TaskTask(unittest.TestCase):
    def setUp(self):
        self.task = Task("Test Task")

    def test_is_active(self):
        self.assertFalse(self.task.is_active())
        self.task.start()
        self.assertTrue(self.task.is_active())
        self.task.stop()
        self.assertFalse(self.task.is_active())

    def test_is_unpaid(self):
        self.assertFalse(self.task.is_unpaid())
        self.task.name = ".Hidden Task"
        self.assertTrue(self.task.is_unpaid())

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

    def test_get_first_start_time(self):
        self.task.add_time_block("3-4")
        self.task.add_time_block("1-2")
        self.task.add_time_block("4-5")
        self.task.add_time_block("2-3")
        self.assertEqual(self.task.get_first_start_time()-today,3600*1)
        self.task = Task('mixed test times')
        self.task.add_time_block("9-1")
        self.task.add_time_block("6-9")
        self.task.add_time_block("8-4")
        self.task.add_time_block("9-2")
        self.assertEqual(self.task.get_first_start_time()-today,3600*6)

    def test_get_last_end_time(self):
        self.task.add_time_block("3-4")
        self.task.add_time_block("1-2")
        self.task.add_time_block("4-5")
        self.task.add_time_block("2-3")
        self.assertEqual(self.task.get_last_end_time()-today,3600*5)
        self.task = Task('mixed test times')
        self.task.add_time_block("0-1")
        self.task.add_time_block("1-9")
        self.task.add_time_block("1-4")
        self.task.add_time_block("1-2")
        self.assertEqual(self.task.get_last_end_time()-today,3600*9)

    def test_get_task_time_range(self):
        self.task.add_time_block("1-2")
        self.task.add_time_block("4-5")
        self.task.add_time_block("2-3")
        self.assertEqual(self.task.get_task_time_range(),'01:00-+>05:00')
        self.task = Task('just one block')
        self.task.add_time_block("9:15-17:30")
        self.assertEqual(self.task.get_task_time_range(),'09:15-->17:30')
        self.task = Task('until now')
        self.task.add_time_block("13-18")
        self.task.add_time_block("13-now")
        self.assertEqual(self.task.get_task_time_range(),'13:00-->now')


class TaskCommandTesks(unittest.TestCase):

    def setUp(self):
        path = './tmp/'
        self.tl = TimeLogger(path,path + today_datetime.strftime("%Y-%m-%d_%A.json"))
        self.tl.tasks = []

    def test_command_prev_day(self):
        self.tl.command_create_rename_merge('example')
        self.assertEqual(len(self.tl.tasks),1)
        self.assertEqual(self.tl.filepath,'./tmp/2023-06-29_Thursday.json')
        self.tl.command_prev_day()
        self.assertEqual(self.tl.filepath,'./tmp/2023-06-28_Wednesday.json')
        self.assertEqual(len(self.tl.tasks),0)
        for _ in range(7*40):
            self.tl.command_prev_day()
        self.assertEqual(self.tl.filepath,'./tmp/2022-09-21_Wednesday.json')


    def test_sub_command_start_new_or_existing_task(self):
        self.assertEqual(len(self.tl.tasks),0)
        
        self.tl.command_create_rename_merge('existing task')
        self.assertEqual(len(self.tl.tasks),1)
        self.assertEqual(len(self.tl.get_task('existing task').time_blocks),1)
        self.assertTrue(self.tl.get_task('existing task').is_active())
        
        self.tl.command_create_rename_merge('existing task')
        self.assertEqual(len(self.tl.tasks),1)
        self.assertEqual(len(self.tl.get_task('existing task').time_blocks),1)
        self.assertTrue(self.tl.get_task('existing task').is_active())

        self.tl.get_task('existing task').stop()
        self.assertFalse(self.tl.get_task('existing task').is_active())

        self.tl.command_create_rename_merge('existing task')
        self.assertEqual(len(self.tl.tasks),1)
        self.assertEqual(len(self.tl.get_task('existing task').time_blocks),2)
        self.assertTrue(self.tl.get_task('existing task').is_active())
        
        self.tl.command_create_rename_merge('new task')
        self.assertEqual(len(self.tl.tasks),2)
        self.assertEqual(len(self.tl.get_task('new task').time_blocks),1)
        self.assertFalse(self.tl.get_task('existing task').is_active())
        self.assertTrue(self.tl.get_task('new task').is_active())
        
        self.tl.command_create_rename_merge('0')
        self.assertEqual(len(self.tl.tasks),2)
        self.assertEqual(len(self.tl.get_task('existing task').time_blocks),3)
        self.assertTrue(self.tl.get_task('existing task').is_active())
        self.assertFalse(self.tl.get_task('new task').is_active())

    def test_sub_command_time_block_to_new_or_existing_task(self):
        self.tl.command_create_rename_merge('missed task=7-8:15')
        self.assertEqual(self.tl.get_task('missed task').get_task_time_range(),'07:00-->08:15')
        self.assertEqual(self.tl.get_task('missed task').get_total_time_spent(),1.25)
        self.tl.command_create_rename_merge('0=6-6:15')
        self.assertEqual(self.tl.get_task('missed task').get_task_time_range(),'06:00-+>08:15')
        self.assertEqual(self.tl.get_task('missed task').get_total_time_spent(),1.5)
        self.assertFalse(self.tl.get_task('missed task').is_active())
        self.tl.command_create_rename_merge('missed task=9-10')
        self.assertEqual(self.tl.get_task('missed task').get_task_time_range(),'06:00-+>10:00')
        self.tl.command_create_rename_merge('missed task=6-10')
        self.assertEqual(self.tl.get_task('missed task').get_task_time_range(),'06:00-->10:00')
        self.tl.command_create_rename_merge('missed task=10:30-now')
        self.assertEqual(self.tl.get_task('missed task').get_task_time_range(),'06:00-+>now')
        self.assertEqual(len(self.tl.get_task('missed task').time_blocks),2)
        self.tl.command_create_rename_merge('missed task=9:45-now')
        self.assertEqual(self.tl.get_task('missed task').get_task_time_range(),'06:00-->now')
        self.assertEqual(len(self.tl.get_task('missed task').time_blocks),1)
        self.tl.command_create_rename_merge('task to be split=5-9')
        self.assertEqual(self.tl.get_task('task to be split').get_total_time_spent(),4)
        self.tl.command_create_rename_merge('spliting task=6-7')
        self.assertEqual(self.tl.get_task('spliting task').get_total_time_spent(),1)
        self.assertEqual(self.tl.get_task('task to be split').get_total_time_spent(),3)

    def test_sub_command_merge(self):
        self.tl.command_create_rename_merge('task 1')
        self.tl.command_create_rename_merge('task 2')
        self.tl.command_create_rename_merge('task 1')
        self.tl.command_create_rename_merge('task 2')
        self.tl.command_create_rename_merge('task 1')
        self.tl.command_create_rename_merge('task 2')
        self.tl.command_create_rename_merge('task 1')
        self.tl.command_create_rename_merge('task 2')
        self.tl.command_create_rename_merge('task 1')
        self.tl.command_create_rename_merge('task 2')
        self.assertEqual(len(self.tl.get_task('task 1').time_blocks),5)
        self.assertEqual(len(self.tl.get_task('task 2').time_blocks),5)
        self.tl.command_create_rename_merge('task 1=task 2')
        self.assertEqual(len(self.tl.get_task('task 1').time_blocks),1)
        self.assertEqual(self.tl.get_task('task 2'),None)

    def test_sub_command_rename(self):
        self.tl.command_create_rename_merge('old name')
        self.assertTrue(self.tl.get_task('old name') is not None)
        self.assertTrue(self.tl.get_task('new name') is None)
        self.tl.command_create_rename_merge('old name=new name')
        self.assertTrue(self.tl.get_task('old name') is None)
        self.assertTrue(self.tl.get_task('new name') is not None)

class TaskAutoCompleter(unittest.TestCase):
    def setUp(self):
        cmds = ['exit','rm ', 'help']
        known_params = ['MEETING','OTHER','SOMETHING']
        self.c = AutoCompleter(cmds, known_params)
        self.c.current_tasks = [Task('TASK-1234'),Task('TASK-42'),Task('OTHER'),Task('record')]

    def test_completer(self):
        self.assertEqual(self.c.complete(''),'exit')
        self.assertEqual(self.c.complete('S'),'SOMETHING')
        self.assertEqual(self.c.complete('noMatch'),None)
        self.assertEqual(self.c.complete('no such '),None)
        self.assertEqual(self.c.complete('no such r'),None)
        self.assertEqual(self.c.complete('e'),'exit')
        self.assertEqual(self.c.complete('ex'),'exit')
        self.assertEqual(self.c.complete('exi'),'exit')
        self.assertEqual(self.c.complete('exit'),None)
        self.assertEqual(self.c.complete('exit '),None)
        self.assertEqual(self.c.complete('h'),'help')
        self.assertEqual(self.c.complete('help '),None)
        self.assertEqual(self.c.complete('r'),'rm ')
        self.assertEqual(self.c.complete('rm'),'rm ')
        self.assertEqual(self.c.complete('rm T'),'rm TASK-1234')
        self.assertEqual(self.c.complete(' '),'TASK-1234')
        self.assertEqual(self.c.complete('8'),None)
        self.assertEqual(self.c.complete('task=8'),'task=8-now')
        self.assertEqual(self.c.complete('task=-8'),None)
        self.assertEqual(self.c.complete('task=8:50'),'task=8:50-now')
        self.assertEqual(self.c.complete('task=8:59'),'task=8:59-now')
        self.assertEqual(self.c.complete('task=8:59-'),'task=8:59-now')
        self.assertEqual(self.c.complete('task=21:12-n'),'task=21:12-now')
        self.assertEqual(self.c.complete('task=11:30-no'),'task=11:30-now')
        self.assertEqual(self.c.complete('task=8:60'),None)
        self.assertEqual(self.c.complete('task=24'),None)
        self.assertEqual(self.c.complete('TASK-42=TASK-1'),'TASK-42=TASK-1234')
        self.assertEqual(self.c.complete('TASK-42=M'),'TASK-42=MEETING')
        self.assertTrue(re.match(r'UNKNOWN=\d{1,2}:(00|15|30|45)-now', self.c.complete('UNKNOWN=')))
        self.assertEqual(self.c.complete('UNKNOWN=M'),None)
        self.assertEqual(self.c.complete('0='),'0=TASK-1234')


if __name__ == '__main__':
    unittest.main()
