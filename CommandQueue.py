import os, sys
import time
import platform
import shlex, subprocess
import multiprocessing

platform_type = platform.system()
cpu_count = multiprocessing.cpu_count()

# file paths
file_lock_path = "./queue.lock"
queue_file_path = "./queue.txt"
temp_queue_file_path = "./~queue.txt"

program_name = sys.argv[0].split('.')[0]

max_processes = cpu_count - 2
lock_poll_interval_s = 5
monitor_refresh_s = 5

process_handles = []
prev_queue_length = 0

def debug(str):
    print("[" + program_name + "] " + str)

def exit(str, ret):
    debug(str)
    debug("Exiting...")
    sys.exit(ret)

def check_file_lock():
    while True:
        try:
            with open(file_lock_path, "x") as lockfile:
                pass
            file_unlock()
            return True
        except FileExistsError:
            return False

def file_lock():
    while True:
        try:
            with open(file_lock_path, "x") as lockfile:
                pass
            break
        except FileExistsError:
            time.sleep(lock_poll_interval_s)

def file_unlock():
    if os.path.exists(file_lock_path):
        os.remove(file_lock_path)
    else:
        debug("How can we unlock a file that doesn't exist? (ERROR)")

def NextCommand():
    # lock file
    file_lock()

    with open(queue_file_path) as file:
        lines = file.readlines()

    if len(lines) > 0:
        command = lines[0].strip()

        with open(temp_queue_file_path, "w") as tempfile:
            tempfile.writelines(lines[1:])

        os.replace(temp_queue_file_path, queue_file_path)

        file_unlock()
        return command
    else:
        file_unlock()
        return None

def QueueLength():
    file_lock()
    with open(queue_file_path) as file:
        lines = file.readlines()
        file_unlock()
        return len(lines)
    file_unlock()

def monitor_loop():
    global prev_queue_length

    idle = True
    printed = False

    while True:
        # resolve processes
        listlen = len(process_handles)
        for x in range(listlen):
            idx = listlen - 1 - x
            if process_handles[idx].poll() == None:
                pass # did not finish
            else:
                del process_handles[idx] # did finish, remove from list

        # try and launch
        scheduled = False
        while len(process_handles) < max_processes:
            command = NextCommand()
            if command == None:
                break
            else:
                scheduled = True
                p = subprocess.Popen(command, shell=True)
                debug("Running command \"" + command +  "\" on Proccess (pid=" + str(p.pid) + ")")
                process_handles.append(p)

        # print new queue length if things have been scheduled
        currentQueueLength = QueueLength()
        if scheduled:
            debug("Currently Running: " + str(len(process_handles)) + ", Pending Queue Size: " + str(currentQueueLength))
            prev_queue_length = currentQueueLength

        if currentQueueLength == 0 and len(process_handles) == 0:
            idle = True
        else:
            idle = False
            printed = False

        if idle == True and printed == False:
            debug("[Scheduler] Queue Empty. Waiting for more commands.")
            printed = True

        # wait
        time.sleep(monitor_refresh_s)


debug("Configuration:")
debug("  Platform: " + platform_type)
debug("  CPU Count: " + str(cpu_count))
debug("  Max Processes: " + str(max_processes))
debug("  Lock Poll Interval: " + str(lock_poll_interval_s) + " seconds")
debug("  Monitor Refresh Interval: " + str(monitor_refresh_s) + " seconds")


if (len(sys.argv) > 1 and sys.argv[1] == "run"):
    if os.path.exists(queue_file_path):
        debug("Queue file found. Using queue file " + os.path.abspath(queue_file_path) + ".")
    else:
        debug("Queue file doesn't exist, creating one. (" + os.path.abspath(queue_file_path) + ")")
        open(queue_file_path, "x").close()
    if check_file_lock():
        debug(" " + program_name + " started.")
        monitor_loop()
    else:
        exit("ERROR: Queue already locked, can't start.", 1)
else:
    file_lock()
    print("Opening queue for editing")
    if platform_type == "Darwin" or \
        platform_type == "Linux":
        #os.system("open -W -n -t " + queue_file_path)
        os.system("vim " + queue_file_path)
    elif platform_type == "Windows":
        os.system(queue_file_path) #?
    else:
        print("Error: unrecognized platform (" + platform_type + ")")
    file_unlock()
    print("Succesfully Updated Queue")
