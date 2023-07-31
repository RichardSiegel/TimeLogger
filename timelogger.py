#/bin/python3

from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta
from enum import Enum
import argparse
import copy
import json
import os
import re
import readline
import sys
import time


class AutoCompleter:
    def __init__(self , cmds = [], known_params = []):
        readline.set_completer(self.complete)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims('\t\n')
        self.cmds = cmds
        self.known_params = known_params
        self.history = []
        self.suggestions = []

    def remove_double_param_use_suggestions(self):
        unique_lst = []
        for item in self.suggestions:
            parts = item.split('=')
            if parts[-1] not in parts[:-1]:
                unique_lst.append(item)
        self.suggestions = unique_lst

    def last_full_quater_time(self):
        current_datetime = datetime.now()
        current_time = current_datetime.time()
        rounded_datetime = current_datetime - timedelta(minutes=current_time.minute % 15)
        rounded_time = rounded_datetime.time()
        return rounded_time.strftime("%H:%M")

    def complete(self, raw_current_input, state = 0):
        if state == 0:
            current_input = raw_current_input.lstrip()
            current_tasks_names = [task.name for task in self.current_tasks]
            current_tasks_ids = [str(i) for i in range(len(self.current_tasks))]
            if raw_current_input == ' ' or raw_current_input == '/':
                self.suggestions = current_tasks_names + self.known_params
            elif current_input == '':
                self.suggestions = self.cmds + ['[Space]+[Tab]:TaskNames']
            else:
                current_prefix = ''
                if "=" in current_input:
                    current_prefix = current_input.rpartition("=")[0] + "="
                else:
                    prefix_list = [cmd for cmd in self.cmds if cmd.endswith(' ')]
                    current_prefix = ([prefix for prefix in prefix_list if current_input.startswith(prefix)]+[''])[0]
                prefixed_params = []
                if "=" not in current_input: 
                    prefixed_params = [current_prefix + name for name in current_tasks_names]
                if "=" in current_input and current_prefix.rstrip("=") in current_tasks_names + current_tasks_ids:
                    prefixed_params = [current_prefix + name for name in current_tasks_names]
                    prefixed_params = prefixed_params + [current_prefix + name for name in self.known_params]
                if current_input.endswith('=') and current_prefix.rstrip("=") not in current_tasks_names + current_tasks_ids:
                    prefixed_params = [current_prefix + self.last_full_quater_time() + '-now']
                possible_suggestions = self.cmds + self.known_params + prefixed_params
                for ending in ['-now','now','ow','w']:
                    if "=" in current_input and TimeBlock.is_valid_range(current_input.rpartition("=")[-1] + ending):
                        possible_suggestions.append(current_input+ending)
                self.suggestions = [cmd for cmd in possible_suggestions + self.history if cmd.lower().startswith(current_input.lower()) and cmd != current_input]
                self.remove_double_param_use_suggestions()
        try:
            return self.suggestions[state]
        except IndexError:
            return None

    def get_cli_input(self, current_tasks, request_test, current_datetime):
        self.current_datetime = current_datetime
        self.current_tasks = current_tasks
        cmd_string = input(request_test)
        # self.history.append(cmd_string)
        return cmd_string

class TimeConflict(Enum):
    UNCHANGED = 1
    SPLIT = 2
    CUTOFF_AT_START = 3
    CUTOFF_AT_END = 4
    REMOVED = 5

# TODO cleanup the type mess, which made this function nessesary
def date_to_datetime(current_time):
    if isinstance(current_time, datetime):
        return current_time
    elif isinstance(current_time, date):
        return datetime(current_time.year, current_time.month, current_time.day)
    else:
        raise ValueError("Input must be a datetime.date or datetime.datetime object")

def now_for_date(source_datetime):
    current_time = datetime.now().time()
    new_datetime = datetime.combine(source_datetime.date(), current_time)
    return new_datetime

class TimeBlock:
    def __init__(self, current_datetime, time_range=None):
        if time_range is None:
            self.start = now_for_date(date_to_datetime(current_datetime)).timestamp()
            self.end = None
        else:
            s, e = time_range.split('-')
            self.start = self.string_to_timestamp(date_to_datetime(current_datetime), s)
            self.end = self.string_to_timestamp(date_to_datetime(current_datetime), e)
        if self.start is None:
            self.end = None
        elif self.end is not None and int(self.start) >= int(self.end):
            self.start = None
            self.end = None

    @staticmethod
    def is_valid_range(time_range):
        if not time_range.count('-') == 1:
            return False
        s, e = time_range.split('-')
        start = TimeBlock.string_to_timestamp(datetime.now(), s)
        end = TimeBlock.string_to_timestamp(datetime.now(), e)
        return start is not None and (end is not None or e == 'now')

    @staticmethod
    def string_to_timestamp(today_datetime, time_string):
        if re.match(r'^(2[0-3]|[0-1]?[0-9])(:[0-5][0-9])?$', time_string) is None:
            return None
        if ':' in time_string:
            h, m = map(int, time_string.split(':'))
            return today_datetime.replace(hour=h, minute=m, second=0, microsecond=0).timestamp()
        else:
            return today_datetime.replace(hour=int(time_string), minute=0, second=0, microsecond=0).timestamp()

    def __repr__(self):
        return self.to_string()

    def to_string(self, split='-'):
        if self.start is None:
            return 'Not Booked...'
        today = int(datetime.fromtimestamp(self.start).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        start_h = int((self.start - today) / 3600)
        start_min = int((float((self.start - today) / 60) - (start_h * 60)))
        start_time = f"{start_h:02d}:{start_min:02d}"
        end_time = 'now'
        if self.end is not None:
            end_h = int((self.end - today) / 3600)
            end_min = int((self.end - today) / 60) - (end_h * 60)
            end_time = f"{end_h:02d}:{end_min:02d}"
        return f"{start_time}{split}{end_time}"

    def to_json(self):
        return {
            'start': self.start,
            'end': self.end
        }

    def __lt__(self, other):
        return self.start < other.start

    def contains_moment(self, timestamp):
        if self.end is None:
            return self.start < timestamp
        return self.start < timestamp and timestamp < self.end

    def stop(self):
        self.end = time.time()

    def none_timestamps_to_inf(self,obj):
        max_timestamp = float('inf')
        obj_copy = copy.deepcopy(obj)
        obj_copy.start = max_timestamp if obj_copy.start is None else obj_copy.start
        obj_copy.end = max_timestamp if obj_copy.end is None else obj_copy.end
        return obj_copy

    def would_be_without(self, block_needing_space):
        old = self.none_timestamps_to_inf(self)
        new = self.none_timestamps_to_inf(block_needing_space)
        if old.start < new.start and old.end > new.end:
            return TimeConflict.SPLIT
        if old.start >= new.start and old.start < new.end and old.end > new.end:
            return TimeConflict.CUTOFF_AT_START
        if old.start < new.start and old.end > new.start and old.end <= new.end:
            return TimeConflict.CUTOFF_AT_END
        if old.start >= new.start and old.end <= new.end:
            return TimeConflict.REMOVED
        return TimeConflict.UNCHANGED

    def without_time_before_end_of(self, block_needing_space):
        new_block = self
        new_block.start = block_needing_space.end
        return new_block

    def without_time_after_start_of(self, block_needing_space):
        new_block = self
        new_block.end = block_needing_space.start
        return new_block

    def time_spent(self):
        if self.start is None:
            return 0
        if self.end is None:
            return float((time.time() - self.start)/ 3600)
        else:
            return float((self.end - self.start)/ 3600)
    

class Task:
    def __init__(self, name, current_datetime):
        self.current_datetime = current_datetime
        self.name = name
        self.description = ""
        self.time_blocks = []

    def is_active(self):
        return len(self.time_blocks) > 0 and self.time_blocks[-1].end is None

    def is_unpaid(self):
        return self.name.startswith('.')

    def start(self):
        if not self.is_active():
            if len(self.time_blocks) > 0 and self.time_blocks[-1].end is None:
                self.stop()
            self.time_blocks.append(TimeBlock(self.current_datetime))

    def stop(self):
        if len(self.time_blocks) > 0 and self.time_blocks[-1].end is None:
            self.time_blocks[-1].stop()

    def add_time_block(self, time_range):
        new_block = time_range
        if isinstance(time_range, str):
            new_block = TimeBlock(self.current_datetime, time_range)
        # Add only valid time blocks
        if new_block.start is not None:
            self.remove_conflicts_with(new_block)
            self.time_blocks.append(new_block)
            self.time_blocks = sorted(self.time_blocks)

    def merge_touching_time_blocks(self):
        merged = False
        for i, time_block in enumerate(self.time_blocks):
            for j, any_other_block  in enumerate(self.time_blocks):
                if i != j:
                    if time_block.end == any_other_block.start:
                        time_block.end = any_other_block.end
                        self.time_blocks.pop(j)
                        merged = True
                        break
        if merged:
            self.merge_touching_time_blocks()

    def remove_conflicts_with(self, conflict_block):
        # Add only valid time blocks
        if conflict_block.start is not None:
            # Remove intersecting
            self.time_blocks = [block for block in self.time_blocks if (block.would_be_without(conflict_block) is not TimeConflict.REMOVED)]
            for block in self.time_blocks:
                conflict = block.would_be_without(conflict_block)
                if conflict is TimeConflict.SPLIT:
                    split_block = copy.deepcopy(block)
                    block.start = conflict_block.end
                    split_block.end = conflict_block.start
                    self.time_blocks.append(split_block)
                elif conflict is TimeConflict.CUTOFF_AT_START:
                    block.start = conflict_block.end
                elif conflict is TimeConflict.CUTOFF_AT_END:
                    block.end = conflict_block.start

    def set_description(self, description):
        self.description = description

    def merge_with(self, task):
        # was_active is used here to overcome the problem with changed order of time-blocks after merging
        was_active=self.is_active()
        if was_active:
            self.stop()
        for block in task.time_blocks:
            self.add_time_block(block)
        task.time_blocks=[]
        if was_active:
            self.start()

    def get_total_time_spent(self):
        total_hours = 0
        for time_block in self.time_blocks:
            total_hours += time_block.time_spent()
        return total_hours

    def __lt__(self, other):
        if self.get_first_start_time() is None or other.get_first_start_time() is None:
            return False
        return self.get_first_start_time() < other.get_first_start_time()

    def get_first_start_time(self):
        if len(self.time_blocks) == 0:
            return None
        if any(block.start is None for block in self.time_blocks):
            return None
        return sorted(self.time_blocks)[0].start

    def get_last_end_time(self):
        if len(self.time_blocks) == 0:
            return None
        if any(block.end is None for block in self.time_blocks):
            return None
        return sorted(self.time_blocks, key=lambda block: block.end)[-1].end

    def get_task_time_range(self):
        task_time_range = TimeBlock(self.current_datetime)
        task_time_range.start = self.get_first_start_time()
        task_time_range.end = self.get_last_end_time()
        if len(self.time_blocks) > 1:
            return task_time_range.to_string('-+>')
        else:
            return task_time_range.to_string('-->')

    def get_json(self):
        data = {
            "name": self.name,
            "description": self.description,
            "time_blocks": [time_block.to_json() for time_block in self.time_blocks]
        }
        return json.dumps(data)

    @staticmethod
    def load_from_json(current_datetime, json_str):
        data = json.loads(json_str)
        name = data["name"]
        description = data["description"]
        time_blocks_data = data["time_blocks"]
        task = Task(name, current_datetime)
        task.description = description
        for x in time_blocks_data:
            block = TimeBlock(current_datetime)
            block.start = x['start']
            block.end = x['end']
            task.time_blocks.append(block)
        return task

class TimeLogger:
    def __init__(self, filepath):
        self.load_file(filepath)

    def load_file(self, filepath):
        path = filepath.split('/')
        self.verbose = False
        self.tasks = []
        self.filepath = filepath
        path = filepath.split('/')
        self.file_name = path[-1]
        self.parrent_dir = path[:-1]
        self.current_datetime = datetime.strptime(self.file_name.split('_')[0], '%Y-%m-%d').date()
        if os.path.isfile(self.filepath):
            self.load_tasks_from_file()
        self.history = []
        self.redo_history = []

    def keep_history(self):
        self.redo_history.clear()
        self.history.append(copy.deepcopy(self.tasks))

    def undo(self):
        if len(self.history) != 0:
            self.redo_history.append(copy.deepcopy(self.tasks))
            self.tasks[:] = self.history.pop()
        else:
            print('Noting to undo!')

    def redo(self):
        if len(self.redo_history) != 0:
            self.history.append(copy.deepcopy(self.tasks))
            self.tasks[:] = self.redo_history.pop()
        else:
            print('Noting to redo!')

    def load_tasks_from_file(self):
        with open(self.filepath, 'r') as file:
            data = json.load(file)
            for task_data in data:
                task = Task.load_from_json(self.current_datetime, task_data)
                self.tasks.append(task)

    def save_tasks_to_file(self):
        if not os.path.exists('/'.join(self.parrent_dir)):
            os.makedirs('/'.join(self.parrent_dir))
        data = [task.get_json() for task in self.tasks]
        with open(self.filepath, 'w') as file:
            json.dump(data, file)

    def task_exists(self,task_name):
        for task in self.tasks:
            if task.name == task_name:
                return True
        return False

    def all_tasks_exist(self,task_refs):
        for task_ref in task_refs:
            if not self.task_exists(task_ref):
                return False
        return True

    def find_task_id(self,task_name):
        for index, task in enumerate(self.tasks):
            if task.name == task_name:
                return index

    def rename_task(self,old_name,new_name):
        if self.task_exists(old_name):
            self.tasks[self.find_task_id(old_name)].name = new_name

    def merge_tasks(self,task_to_keep,task_to_consume):
        keep_id = self.find_task_id(task_to_keep)
        consume_id = self.find_task_id(task_to_consume)
        self.tasks[keep_id].merge_with(self.tasks[consume_id])
        del self.tasks[consume_id]

    def get_current_task(self):
        for task in self.tasks:
            if task.is_active():
                return task
        return None

    def stop_current_task(self):
        for task in self.tasks:
            task.stop()

    def create_task(self,task_name):
        self.tasks.append(Task(task_name, self.current_datetime))

    def start_task(self,task_name):
        for task in self.tasks:
            if task.name == task_name:
                task.start()
                return
        new_task = Task(task_name, self.current_datetime)
        self.tasks.append(new_task)
        self.tasks[-1].start()

    def format_hours(self,hours):
        h = int(hours)
        m = int((hours - int(hours)) * 60)
        if h == 0:
            return f"{m}m"
        else:
            return f"{h}h+{m}m"

    def show_task_summary(self):
        total_logged_time = self.format_hours(sum(task.get_total_time_spent() for task in self.tasks))
        visible_tasks = [task for task in self.tasks if not task.is_unpaid()]
        total_working_time = self.format_hours(sum(task.get_total_time_spent() for task in visible_tasks))
        print(f"Total logged time: {total_logged_time}")
        if not total_logged_time == total_working_time:
            print(f"Total working time: {total_working_time}")
        print()
        for index, task in enumerate(self.tasks):
            total_time = self.format_hours(task.get_total_time_spent()).rjust(7,'.')
            task_time_range = task.get_task_time_range()
            pointer = '>' if task.is_active() else '.'
            fill = '..' if task.is_active() else ''
            print(f"{index:02d} {pointer} {total_time} {task_time_range}{fill} {pointer} {pointer} {pointer} {task.name}")

    def show_task_percentages(self):
        visible_tasks = [task for task in self.tasks if not task.is_unpaid()]
        total_time = sum(task.get_total_time_spent() for task in visible_tasks)
        rounded_percentages = []
        for task in visible_tasks:
            task_percentage = 0
            try:
                task_percentage = (task.get_total_time_spent() / total_time) * 100
            except:
                pass
            rounded_percentage = round(task_percentage)
            rounded_percentages.append(rounded_percentage)
        # Adjust the last percentage to ensure the sum is 100
        correction = 100 - sum(rounded_percentages)
        if rounded_percentages:
            rounded_percentages[-1] += correction
        # Print the task names and percentages
        for i, task in enumerate(visible_tasks):
                print(f"{task.name} {rounded_percentages[i]}%;", end=" ")
        if visible_tasks and correction != 0:
            print()
            print()
            print(f"Percent correction on last task to ensure sum of 100%: {correction}%")

    def task_id_to_name(self,possible_id):
        if self.task_exists(possible_id):
            return possible_id
        if possible_id.isdigit() and int(possible_id)>=0 and int(possible_id)<len(self.tasks):
            return self.tasks[int(possible_id)].name
        return possible_id

    # TODO test
    def command_remove(self,command):
        if self.verbose:
            print("command_remove")
        task_name = self.task_id_to_name(' '.join(command.split(' ')[1:]))
        if self.task_exists(task_name):
            del self.tasks[self.find_task_id(task_name)]

    # TODO test
    def command_stop(self):
        if self.verbose:
            print("command_stop")
        self.stop_current_task()

    def command_help(self):
        if self.verbose:
            print("command_help")
        print("'<' OR '>'                      load previous or next day")
        print("''                              update view")
        print("'rm [name/id]'                  to delete")
        print("'stop' OR 'x'                   to stop current task")
        print("'undo' OR 'redo'                to undo/redo the last change")
        print("'[name/id]=[name/id]=[name/id]' to rename, merge and create")
        print("    'some task name'             to create 'some task name'")
        print("    '.some hidden task'          to create a non-main-work task")
        print("    'a=b'                        to merge b into a")
        print("    'a=b=c'                      to merge b and c into a")
        print("    'a=new_task_name'            to rename a")
        print("    'a=12:15-18'                 to create a from 12:15 to 18:00")
        print("    'a=9-now'                    to create unclosed task a starting 9:00")
        print("'exit' OR 'q'                   close time logger CLI")
        print("")
        print("WARNING: editing old recordeds (by passing a path like .timelogger/*.json) may not work as expacted.")
        print("")


    def convert_to_task_refs(self,command):
        return [self.task_id_to_name(task_ref) for task_ref in command.split('=')]

    def get_task(self,task_ref):
        if self.task_exists(task_ref):
            return self.tasks[self.find_task_id(task_ref)]
        return None

    # TODO test
    def normalize_tasks(self):
        for task in self.tasks:
            task.merge_touching_time_blocks()
        self.tasks = sorted(self.tasks)

    def command_create_rename_merge(self,command):
        if self.verbose:
            print("command_create_rename_merge")
        task_refs = self.convert_to_task_refs(command)
        if len(task_refs) == 1:
            self.sub_command_start_new_or_existing_task(task_refs[0])
        elif len(task_refs) == 2 and TimeBlock.is_valid_range(task_refs[1]):
            self.sub_command_time_block_to_new_or_existing_task(task_refs[0],task_refs[1])
        elif self.all_tasks_exist(task_refs):
            self.sub_command_merge(task_refs)
        elif self.all_tasks_exist(task_refs[:-1]) and not self.task_exists(task_refs[-1]):
            self.sub_command_merge(task_refs[:-1])
            self.sub_command_rename(task_refs)
        self.normalize_tasks()

    def sub_command_start_new_or_existing_task(self,task_ref):
        if self.verbose:
            print("sub_command_start_new_or_existing_task")
        last_active_task = self.get_current_task()
        if not self.task_exists(task_ref):
            self.create_task(task_ref)
        self.get_task(task_ref).start()
        if last_active_task is not None and last_active_task is not self.get_task(task_ref):
            last_active_task.stop()

    def sub_command_time_block_to_new_or_existing_task(self,task_ref, time_range):
        if self.verbose:
            print("sub_command_time_block_to_new_or_existing_task")
        for task in self.tasks:
            task.remove_conflicts_with(TimeBlock(self.current_datetime, time_range))
        if not self.task_exists(task_ref):
            self.create_task(task_ref)
        self.get_task(task_ref).add_time_block(time_range)

    def sub_command_merge(self,task_refs):
        if self.verbose:
            print("sub_command_merge")
        for task_ref in task_refs[1:]:
            self.merge_tasks(task_refs[0],task_ref)

    def sub_command_rename(self,task_refs):
        if self.verbose:
            print("sub_command_rename")
        self.rename_task(task_refs[0],task_refs[-1])

    def command_next_day(self):
        previous_date = self.current_datetime + relativedelta(days=1)
        path_elements = self.parrent_dir + [previous_date.strftime('%Y-%m-%d_%A.json')]
        path = '/'.join(self.parrent_dir)+'/'
        filepath = '/'.join(path_elements)
        self.load_file(filepath)

    def command_prev_day(self):
        previous_date = self.current_datetime - relativedelta(days=1)
        path_elements = self.parrent_dir + [previous_date.strftime('%Y-%m-%d_%A.json')]
        path = '/'.join(self.parrent_dir)+'/'
        filepath = '/'.join(path_elements)
        self.load_file(filepath)
        

def load_lines_to_list(file_path):
    with open(file_path, "r") as file:
        lines = [line.strip() for line in file.readlines()]
    return lines


def main():
    path = './.timelogger/'
    filepath = path + datetime.now().strftime("%Y-%m-%d_%A.json")
    auto_complete_filepath = path + 'auto_complete.csv'

    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.endswith('.json'):
                filepath = arg

    tl = TimeLogger(filepath)
    auto_complete_list = ["Example auto complete", "Add a list of auto-completions as .timelogger/auto_complete.csv"]
    if os.path.exists(auto_complete_filepath):
        auto_complete_list = load_lines_to_list(auto_complete_filepath)
    completer = AutoCompleter(['exit', 'rm ', 'stop', 'help', 'undo', 'redo'], auto_complete_list)
    command = ''
    params = []
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        if command == "":
            pass
        elif command == "exit" or command == "q":
            break
        elif command == ">":
            tl.command_next_day()
        elif command == "<":
            tl.command_prev_day()
        elif command.startswith("rm "):
            tl.keep_history()
            tl.command_remove(command)
        elif command == "stop" or command == "x":
            tl.keep_history()
            tl.command_stop()
        elif command == "exit":
            break
        elif command == "undo":
            tl.undo()
        elif command == "redo":
            tl.redo()
        elif command == "help":
            tl.command_help()
        else:
            tl.keep_history()
            tl.command_create_rename_merge(command)

        if command != "help":
            tl.save_tasks_to_file()

            print('LOG stored in: ' + tl.filepath)
            print()
            tl.show_task_summary()
            print()
            tl.show_task_percentages()
            print()
        print()

        command = completer.get_cli_input(tl.tasks, '\n[Tab] to auto-complete > ', tl.current_datetime).strip()

if __name__ == "__main__":
    main()

