import statistics

class Task:
    def __init__(self, id, arrival_time, burst_time):
        self.id = id
        self.arrival_time = arrival_time
        self.start_time = None
        self.finish_time = None
        self.remaining_time = burst_time
        self.burst_time = burst_time
        self.core_id = None
        self.waiting_time = 0
        self.turnaround_time = 0
        self.utilization = 0
        self.predicted_burst = 5   #initial guess
        self.last_actual_burst = None


class Core:
    def __init__(self, id, speed=1):
        self.id = id
        self.current_task = None
        self.task_queue = []  # Queue for tasks assigned to this core
        self.time_slice = 1  # Time slice for round-robin scheduling
        self.active_time = 0  # Time spent on the current task
        self.preemption_count = 0  # Count of preemptions
        self.time_line = []  # Timeline of task execution
        self.speed = speed  # Speed of the core

def reset_simulation():
    global current_time, global_queue, tasks, cores
    current_time = 0
    global_queue = []  # Global queue for tasks
    cores = [Core(0,speed=2), Core(1,speed=1)]
    #tasks = [
    #Task(1, arrival_time=0, burst_time=10),  # Long task starts early
    #Task(2, arrival_time=1, burst_time=1),   # Short task risks getting stuck
    #Task(3, arrival_time=2, burst_time=2),   # Medium task, arrives behind long
    #Task(4, arrival_time=3, burst_time=1),   # Another short task
    #Task(5, arrival_time=4, burst_time=2),   # Could be delayed
    #Task(6, arrival_time=5, burst_time=1),   # May experience starvation
#]
    tasks = [Task(i, arrival_time=i//4, burst_time=(i % 10 + 1)) for i in range(1, 101)]



def burst_estimator(task):
    alpha = 0.5  # Smoothing factor for burst time prediction
    actual_burst = task.burst_time
    previous_prediction = task.predicted_burst
    task.last_actual_burst = actual_burst
    task.predicted_burst = (alpha * actual_burst) + ((1 - alpha) * previous_prediction)
    return task.predicted_burst            

def assign_tasks_to_queue(tasks):
    max_queue_length = 2  # Maximum length of the task queue for each core
    burst_threshold = 5  # Threshold for burst time prediction
    new_tasks = [task for task in tasks if task.arrival_time == current_time ]
    
    for task in new_tasks:        
        predicted = task.predicted_burst
        #print(f"Task {task.id} predicted burst time: {predicted:.2f}")
        if predicted >= burst_threshold:
            target_core = max(cores, key=lambda c: c.speed)
        else:
            target_core = min(cores, key=lambda c: c.speed)
           
        # hybrid queue decision
        if len(target_core.task_queue) < max_queue_length:
            target_core.task_queue.append(task)
        else:
            # If the queue is full, add to the global queue
            if ENABLE_GLOBAL_QUEUE:
                global_queue.append(task)
            else:
                fallback_core = min(cores, key=lambda c: len(c.task_queue))
                fallback_core.task_queue.append(task)

        
def assign_task_to_core(core):
    if core.current_task is None and core.task_queue:
        core.task_queue.sort(key=lambda t: t.predicted_burst)
        #print(f"🔍 Core {core.id} queue order: {[f'T{t.id}:{t.predicted_burst:.1f}' for t in core.task_queue]}")
        next_task = core.task_queue.pop(0)
        core.current_task = next_task
        if next_task.start_time is None:
            next_task.start_time = current_time
        next_task.core_id = core.id
        core.time_slice = 0  # Reset time slice for the new task
        #if core.current_task:
           # print(f"🟢 Time {current_time}: Core {core.id} assigned Task {core.current_task.id} (pred: {core.current_task.predicted_burst})")


def metrics(tasks):
    waiting_times = []
    turnaround_times = []
    utilizations = []
    
    for core in cores:
        utilization = core.active_time / (current_time + 1) * 100 if core.active_time > 0 else 0
        utilizations.append(utilization)

    for task in tasks:
        waiting_times.append(task.waiting_time)
        turnaround_times.append(task.turnaround_time)
    
    # statistics metrics
    std_dev = statistics.stdev(waiting_times)
    avg_waiting_time = statistics.mean(waiting_times)
    avg_turnaround_time = statistics.mean(turnaround_times)
    avg_utilization = statistics.mean(utilizations)
    print(f"Average Waiting Time: {avg_waiting_time:.2f}")
    print(f"Standard Deviation of Waiting Time: {std_dev:.2f}")
    print(f"Average Turnaround Time: {avg_turnaround_time:.2f}")
    print(f"Average Utilization: {avg_utilization:.2f}")

def print_task_queue(core):
    print("Gantt-style timeline:")
    print("Time:    ", end="")
    for i in range(current_time):
        print(f"{i:<6}", end="")
    print("")
    for core in cores:
        print(f"Core {core.id}: ", end="")
        for task in core.time_line:
            print(f" {task:<5}", end="")
        print()
    print("\n")
    #print("\n📊 Final Burst Prediction for Each Task:")
    #for task in tasks:
     #   print(f"Task {task.id}: Predicted = {task.predicted_burst:.2f}, Actual = {task.burst_time}")
    #print("\n")

       
def starvation_check(core):
    starvation_threshold = 2  # force early rescue for testing
    short_task_threshold = 3  # define what we consider a "short" task

    for task in core.task_queue[:]:
        waiting_duration = current_time - task.arrival_time
        if task.start_time is None and waiting_duration > starvation_threshold:
            core.task_queue.remove(task)

            if ENABLE_GLOBAL_QUEUE:
                global_queue.append(task)
                #print(f"🛑 Rescuing Task {task.id} (waited {waiting_duration}) to GLOBAL queue")
            else:
                other_cores = [c for c in cores if c != core]
                if not other_cores:
                    # If no other core available, reinsert into same core
                    core.task_queue.append(task)
                 #   print(f"⚠️ Only one core available. Task {task.id} returned to same Core {core.id}")
                    continue

                least_loaded = min(other_cores, key=lambda c: len(c.task_queue))

                if task.burst_time <= short_task_threshold:
                    least_loaded.task_queue.insert(0, task)
                  #  print(f"🛑 Rescuing SHORT Task {task.id} (waited {waiting_duration}) from Core {core.id} to Core {least_loaded.id} (front)")
                else:
                    least_loaded.task_queue.append(task)
                   # print(f"🛑 Rescuing LONG Task {task.id} (waited {waiting_duration}) from Core {core.id} to Core {least_loaded.id} (end)")


def steal_task(core):
    if core.current_task is None and not core.task_queue:
        for other_core in cores:
            if other_core != core and other_core.task_queue: 
                stolen_task = other_core.task_queue.pop(0)
                core.task_queue.append(stolen_task)
                assign_task_to_core(core)
                return
        if ENABLE_GLOBAL_QUEUE and global_queue:
            pulled_task = global_queue.pop(0)
            core.task_queue.append(pulled_task)
            assign_task_to_core(core)
            return

    
def run_experiment(enable_starvation, enable_stealing, enable_global, title):
    global ENABLE_STARVATION, ENABLE_STEALING, ENABLE_GLOBAL_QUEUE, current_time
    ENABLE_STARVATION = enable_starvation
    ENABLE_STEALING = enable_stealing
    ENABLE_GLOBAL_QUEUE = enable_global
    quantum = 2  # Time slice for round-robin scheduling


    print(f"\n === Runnign Experiment: {title} ===")

    reset_simulation()

    while not all(task.finish_time is not None for task in tasks):

        assign_tasks_to_queue(tasks)
                
        for core in cores:
            assign_task_to_core(core)
            if ENABLE_STARVATION:
                starvation_check(core)
            if ENABLE_STEALING:
                steal_task(core)

        # run the core to execute the task by Round Robin
        for core in cores:
            if core.current_task: 
                core.active_time += 1
                core.time_slice += 1 
                core.current_task.remaining_time -= core.speed
                if core.current_task.remaining_time < 0:
                    core.current_task.remaining_time = 0
                
                if core.current_task.remaining_time == 0:
                    finished_task = core.current_task
                    finished_task.finish_time = current_time + 1
                    finished_task.waiting_time = finished_task.start_time - finished_task.arrival_time
                    finished_task.turnaround_time = finished_task.finish_time - finished_task.arrival_time
                    burst_estimator(finished_task)
                    core.current_task = None
                    core.time_slice = 0
                    assign_task_to_core(core)
                    
                elif core.time_slice == quantum:
                    core.preemption_count += 1
                    core.task_queue.append(core.current_task)
                    core.current_task = None
                    core.time_slice = 0
                    assign_task_to_core(core)

        # update the timeline for each core
        for core in cores:
            if core.current_task:
                core.time_line.append(core.current_task.id)
            else:
                core.time_line.append("Idle")

        current_time +=1 
    #print_task_queue(cores)
    metrics(tasks)

run_experiment(False, False, False, "No Starvation, No Stealing, No Global Queue")
#run_experiment(True, False, False, "Starvation, No Stealing, No Global Queue")
run_experiment(False, True, False, "No Starvation, Stealing, No Global Queue")
run_experiment(True, True, False, "Starvation, Stealing, No Global Queue")
#run_experiment(False, False, True, "No Starvation, No Stealing, Global Queue")
#run_experiment(True, False, True, "Starvation, No Stealing, Global Queue")
#run_experiment(False, True, True, "No Starvation, Stealing, Global Queue")
run_experiment(True, True, True, "Starvation, Stealing, Global Queue")

