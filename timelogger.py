#/bin/python3

from datetime import datetime
from enum import Enum
import argparse
import json
import time
import os
import re
import copy

class TimeConflict(Enum):
    UNCHANGED = 1
    SPLIT = 2
    CUTOFF_AT_START = 3
    CUTOFF_AT_END = 4
    REMOVED = 5

class TimeBlock:
    def __init__(self, time_range=None):
        if time_range is None:
            self.start = time.time()
            self.end = None
        else:
            s, e = time_range.split('-')
            self.start = self.string_to_timestamp(s)
            self.end = self.string_to_timestamp(e)
        if self.start is None:
            self.end = None
        elif self.end is not None and int(self.start) >= int(self.end):
            self.start = None
            self.end = None

    # TODO test
    @staticmethod
    def is_valid_range(time_range):
        s, e = time_range.split('-')
        start = TimeBlock.string_to_timestamp(s)
        end = TimeBlock.string_to_timestamp(e)
        return start is not None and (end is not None or e == 'now')

    @staticmethod
    def string_to_timestamp(time_string):
        if re.match(r'^(2[0-3]|[0-1]?[0-9])(:[0-5][0-9])?$', time_string) is None:
            return None
        if ':' in time_string:
            h, m = map(int, time_string.split(':'))
            return datetime.now().replace(hour=h, minute=m, second=0, microsecond=0).timestamp()
        else:
            return datetime.now().replace(hour=int(time_string), minute=0, second=0, microsecond=0).timestamp()

    def __repr__(self):
        return self.to_string()

    def to_string(self):
        today = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        start_h = int((self.start - today) / 3600)
        start_min = int((float((self.start - today) / 60) - (start_h * 60)))
        start_time = f"{start_h:02d}:{start_min:02d}"
        end_time = 'now'
        if self.end is not None:
            end_h = int((self.end - today) / 3600)
            end_min = int((self.end - today) / 60) - (end_h * 60)
            end_time = f"{end_h:02d}:{end_min:02d}"
        return f"{start_time}-{end_time}"

    def to_json(self):
        return {
            'start': self.start,
            'end': self.end
        }

    def __lt__(self, other):
        return self.start < other.start

    def stop(self):
        self.end = time.time()

    def whould_be_without(self, block_to_remove):
        if block_to_remove.end is None:
            return TimeConflict.UNCHANGED
        if self.start < block_to_remove.start and self.end > block_to_remove.end:
            return TimeConflict.SPLIT
        if self.start >= block_to_remove.start and self.start < block_to_remove.end and self.end > block_to_remove.end:
            return TimeConflict.CUTOFF_AT_START
        if self.start < block_to_remove.start and self.end > block_to_remove.start and self.end <= block_to_remove.end:
            return TimeConflict.CUTOFF_AT_END
        if self.start >= block_to_remove.start and self.end <= block_to_remove.end:
            return TimeConflict.REMOVED
        else:
            return TimeConflict.UNCHANGED

    def without_time_before_end_of(self, block_to_remove):
        new_block = self
        new_block.start = block_to_remove.end
        return new_block

    def without_time_after_start_of(self, block_to_remove):
        new_block = self
        new_block.end = block_to_remove.start
        return new_block

    # TODO calculate all times (also down the line) without the time block until now (to not count time double)
    def get_houres(self):
        if self.start is None:
            return 0
        if self.end is None:
            return float((time.time() - self.start)/ 3600)
        else:
            return float((self.end - self.start)/ 3600)
    

class Task:
    def __init__(self, name):
        self.name = name
        self.description = ""
        self.time_blocks = []

    def is_active(self):
        return len(self.time_blocks) > 0 and self.time_blocks[-1].end is None

    def is_unpaid(self):
        return self.name.startswith('.')

    def start(self):
        if len(self.time_blocks) > 0 and self.time_blocks[-1].end is None:
            self.stop()
        self.time_blocks.append(TimeBlock())

    def stop(self):
        if len(self.time_blocks) > 0 and self.time_blocks[-1].end is None:
            self.time_blocks[-1].stop()

    def add_time_block(self, time_range):
        new_block = time_range
        if isinstance(time_range, str):
            new_block = TimeBlock(time_range)
        # Add only valid time blocks
        if new_block.start is not None:
            self.remove_conflicts_with(new_block)
            self.time_blocks.append(new_block)
            self.time_blocks = sorted(self.time_blocks)

    def remove_conflicts_with(self, conflict_block):
        # Add only valid time blocks
        if conflict_block.start is not None:
            # Remove intersecting
            self.time_blocks = [block for block in self.time_blocks if (block.whould_be_without(conflict_block) is not TimeConflict.REMOVED)]
            for block in self.time_blocks:
                conflict = block.whould_be_without(conflict_block)
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
            total_hours += time_block.get_houres()
        return total_hours

    def get_json(self):
        data = {
            "name": self.name,
            "description": self.description,
            "time_blocks": [time_block.to_json() for time_block in self.time_blocks]
        }
        return json.dumps(data)

    @staticmethod
    def load_from_json(json_str):
        data = json.loads(json_str)
        name = data["name"]
        description = data["description"]
        time_blocks_data = data["time_blocks"]
        task = Task(name)
        task.description = description
        for x in time_blocks_data:
            block = TimeBlock()
            block.start = x['start']
            block.end = x['end']
            task.time_blocks.append(block)
        return task

path='./.timelogger/'
def generate_filename():
    now = datetime.now()
    return now.strftime("%Y-%m-%d_%A.json")

def load_tasks_from_file(task):
    filename=path+generate_filename()
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            data = json.load(file)
            for task_data in data:
                task = Task.load_from_json(task_data)
                tasks.append(task)
    return tasks

def save_tasks_to_file(tasks):
    if not os.path.exists(path):
        os.makedirs(path)
    data = [task.get_json() for task in tasks]
    with open(path+generate_filename(), 'w') as file:
        json.dump(data, file)

def task_exists(task_name):
    for task in tasks:
        if task.name == task_name:
            return True
    return False

def find_task_id(task_name):
    for index, task in enumerate(tasks):
        if task.name == task_name:
            return index

def rename_task(old_name,new_name):
    if task_exists(old_name):
        tasks[find_task_id(old_name)].name = new_name

def merge_tasks(task_to_keep,task_to_consume):
    keep_id = find_task_id(task_to_keep)
    consume_id = find_task_id(task_to_consume)
    tasks[keep_id].merge_with(tasks[consume_id])
    del tasks[consume_id]

def stop_current_task():
    for task in tasks:
        task.stop()

def create_task(task_name):
    tasks.append(Task(task_name))

def start_task(task_name):
    for task in tasks:
        if task.name == task_name:
            task.start()
            return
    new_task = Task(task_name)
    tasks.append(new_task)
    tasks[-1].start()

def show_task_summary(tasks):
    print("")
    for index, task in enumerate(tasks):
        total_time = task.get_total_time_spent()
        pointer = '>' if task.is_active() else ' '
        print(f"{index:02d} {pointer} {total_time:.2f}h  {task.name}")
    total_logged_time = sum(task.get_total_time_spent() for task in tasks)
    visible_tasks = [task for task in tasks if not task.is_unpaid()]
    total_working_time = sum(task.get_total_time_spent() for task in visible_tasks)
    print()
    print(f"Total logged time: {total_logged_time:.2f} hours")
    if not total_logged_time == total_working_time:
        print(f"Total working time: {total_working_time:.2f} hours")

def show_task_percentages(tasks):
    visible_tasks = [task for task in tasks if not task.is_unpaid()]
    total_time = sum(task.get_total_time_spent() for task in visible_tasks)
    rounded_percentages = []
    for task in visible_tasks:
        task_percentage = (task.get_total_time_spent() / total_time) * 100
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
        print(f"Percent correction on last task to ensure sum of 100%: {correction}%")

def task_id_to_name(possible_id):
    if task_exists(possible_id):
        return possible_id
    if possible_id.isdigit() and int(possible_id)>=0 and int(possible_id)<len(tasks):
        return tasks[int(possible_id)].name
    return possible_id

tasks = []
tasks = load_tasks_from_file(tasks)
def main():
    command = ''
    params = []
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        if command == "":
            pass
        elif command == "exit" or command == "q":
            break
        elif command.startswith("rm "):
            task_name = task_id_to_name(command.split(' ')[1])
            if task_exists(task_name):
                del tasks[find_task_id(task_name )]
        elif command == "stop" or command == "x":
            stop_current_task()
        elif command == "help":
            print("''                              update view")
            print("'rm [name/id]'                  to delete")
            print("'stop' OR 'x'                   to stop current task")
            print("'[name/id]=[name/id]=[name/id]' to rename, merge and create")
            print("    'a=b'                        to merge b into a")
            print("    'a=b=c'                      to merge b and c into a")
            print("    'a=new_task_name'            to rename a")
            print("    'a=12:15-18'                 to create a from 12:15 to 18:00")
            print("    'a=9-now'                    to create unclosed task a starting 9:00")
            print("    WARNING: New Task overwrite existing tasks at the same time.")
            print("             Try not to clash tasks if you want to be sure.")
            print("             * This will be improved in the future.")
            print("'exit' OR 'q'                   close time logger CLI")
        else:
            if not params:
                # Create new Task
                stop_current_task()
                start_task(command)
            else:
                if not task_exists(command):
                    create_task(command)
                if TimeBlock.is_valid_range(params[0]):
                    # Add new task (eg.: taskName=12:30-now )
                    if params[0].endswith('now'):
                        stop_current_task()
                    else:
                        for task in tasks:
                            task.remove_conflicts_with(TimeBlock(params[0]))
                    tasks[find_task_id(command)].add_time_block(params[0])
                    print('TODO remove conflicting time periodes (do a y/n dialog)')
                    print('TODO handle end times in the future. (auto change to now and notify user)')
                else:
                    # Merge or Rename task
                    # input: command=param=param2
                    # - if param exists --> time for param is added to command && param is removed
                    # - if not param exists -->  rename command to param
                    # - if only param2 not exists -->  rename command to param2 (after merge with param)
                    for param in params:
                        if not task_exists(param):
                            # TODO warn/fail if more than 1 param
                            rename_task(command,param)
                        else:
                            # TODO warn/fail if more than last one do not exist as task
                            # edge-case? renamed command before trying to merge
                            merge_tasks(command,param)

        save_tasks_to_file(tasks)
        show_task_percentages(tasks)
        print()
        show_task_summary(tasks)
        print()
        line = []
        for part in input("Enter a task (name/id) or command (help): ").strip().split('='):
            if not task_exists(part) and part.isdigit() and int(part)>=0 and int(part)<len(tasks):
                line.append(tasks[int(part)].name)
            else:
                line.append(part)
        command = line[0]
        params = line[1:]


if __name__ == "__main__":
    main()

