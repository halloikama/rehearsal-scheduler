import pandas as pd
from math import log
from math import exp
from random import random
from random import randint
import time
import numpy as np


def safe_exp(x):
    try:
        return exp(x)
    except:
        return 0


def update_t(step, t_min, t_max, step_max):
    new_t = t_min + (t_max - t_min) * ((step_max - step)/step_max)
    return new_t


def get_actor_call_times(state, name_list, scene_time, sa_matrix):
    # get what the first scene is when people need to attend
    n_actors = len(name_list)
    nr_calls = [0]*len(state)
    actor_call_time = [None]*n_actors
    for actor_ix, actor in enumerate(sa_matrix.T):
        attend = actor[state]
        # print(attend)
        for i in range(1, len(attend)+1):
            call_slice = attend[0:i]
            # print(call_slice)
            call_test = (i-1)*[0]+[1]
            # print(call_test)

            if (call_slice == call_test).all():
                actor_call_time[actor_ix] = i
                nr_calls[i-1] += 1

    # get info in nice dict form
    call_time_dict = {}

    temp = np.array(scene_time)
    len_state_scenes = list(temp[state])
    for ix, call_scene in enumerate(actor_call_time):
        if call_scene != None:
            call_time_dict[name_list[ix]] = sum(
                len_state_scenes[0:call_scene-1])
        else:
            call_time_dict[name_list[ix]] = 'N/A'

    return call_time_dict


def get_neighbors(current_state, n_actors, n_scenes):
    what_operation = randint(1, 5)
    neighbor_canidate = current_state.copy()
    # remove scene
    if what_operation == 1:
        if len(neighbor_canidate) < 2:
            return neighbor_canidate
        else:
            rm_scene = randint(0, len(current_state)-1)
            neighbor_canidate.pop(rm_scene)
            return neighbor_canidate

    # add scene
    elif what_operation == 2:
        if len(neighbor_canidate) == n_scenes:
            return neighbor_canidate
        else:
            pick_a_scene = randint(0, n_scenes-1)
            while pick_a_scene in neighbor_canidate:
                pick_a_scene = randint(0, n_scenes-1)
            neighbor_canidate.append(pick_a_scene)
            return neighbor_canidate

    # swap scene with scene not in proposal
    elif what_operation == 3 or what_operation == 4:
        
        if len(neighbor_canidate) == n_scenes or len(neighbor_canidate) == 0:
            return neighbor_canidate
        else:
            pick_a_scene = randint(0, n_scenes-1)
            while pick_a_scene in neighbor_canidate:
                pick_a_scene = randint(0, n_scenes-1)
            rm_scene = randint(0, len(current_state)-1)
            neighbor_canidate[rm_scene] = pick_a_scene
            return neighbor_canidate

    # swap order of scenes in proposal
    elif what_operation == 5:
        if len(neighbor_canidate) < 2:
            return neighbor_canidate
        else:
            p0 = randint(0, len(neighbor_canidate)-1)
            p1 = randint(0, len(neighbor_canidate)-1)

            neighbor_canidate[p0] = current_state[p1]
            neighbor_canidate[p1] = current_state[p0]

            return neighbor_canidate


def get_total_time(proposal, max_hours, min_hours, scene_time):
    time = 0
    for e in proposal:
        time = time + scene_time[e]
    if time > max_hours*60 or time < min_hours*60:
        return 9999999
    else:
        return 0


def get_waiting_time(proposal, sa_matrix, scene_time, actors_to_ignore):
    # set actors to ignore (in this case 3 and 5 who always have to attend the whole day)
    state = proposal

    single_scene_show = 0
    cum_wait_period = 0
    nr_calls = [0]*len(state)
    for actor_ix, actor in enumerate(sa_matrix.T):

        # ignore actors who always have to be there
        if actor_ix in actors_to_ignore:
            continue

        actor_attend = actor[state]

        # add penalty for an actor only having to show up for a single scene
        if sum(actor_attend) == 1:
            single_scene_show += 99999

        # calculate the number of calls per scene
        for i in range(1, len(actor_attend)+1):
            call_slice = actor_attend[0:i]
            call_test = (i-1)*[0]+[1]

            if (call_slice == call_test).all():
                nr_calls[i-1] += 1

        has_to_attend = 0
        possible_wait_period = 0
        wait_period = 0
        # go through the selected state scenes per actor and see if the actor has to attend
        for scene_attendance_ix, attend in enumerate(actor_attend):
            # change default if actor has to attend
            if attend == 1 and has_to_attend == 0:
                has_to_attend = 1

            # add waiting time if actor has to wait after having to attend
            if has_to_attend == 1 and attend == 0:
                current_scene = state[scene_attendance_ix]
                possible_wait_period += scene_time[current_scene]

            # if actor has a scene after (i.e. cannot go home) add possible wait time to real wait time
            if possible_wait_period > 0 and attend == 1:
                wait_period = wait_period + possible_wait_period
                possible_wait_period = 0

        # add actor waiting time to cumulative waiting time
        cum_wait_period = cum_wait_period + wait_period

    scene_has_call = [call > 0 for call in nr_calls]
    nr_call_periods = sum(scene_has_call)

    # TODO: refine call penalty, set ideal number of calls per hour
    call_penalty = 0
    if nr_call_periods/len(state) > 0.5:
        call_penalty = (nr_call_periods/len(state)-0.5)**2*5000

    return cum_wait_period, single_scene_show, call_penalty


def get_include_avoid_penalty(proposal, scenes_to_include, scenes_to_avoid):
    scenes_to_include0 = set([scene - 1 for scene in scenes_to_include])
    scenes_to_avoid0 = set([scene - 1 for scene in scenes_to_avoid])
    proposal = set(proposal)

    avoid_penalty = 0
    include_penalty = 0

    if proposal & scenes_to_avoid0:
        avoid_penalty += 99999
    if not scenes_to_include0.issubset(proposal):
        include_penalty += 99999

    return include_penalty, avoid_penalty


def cost(proposal, max_hours, min_hours, sa_matrix, scene_time, actors_to_ignore, scenes_to_include, scenes_to_avoid, verbose=False):

    time_cost = get_total_time(proposal, max_hours, min_hours, scene_time)
    waiting_cost, single_scene_penalty, call_penalty = get_waiting_time(
        proposal, sa_matrix, scene_time, actors_to_ignore)
    include_penalty, avoid_penalty = get_include_avoid_penalty(
        proposal, scenes_to_include, scenes_to_avoid)

    time_cost_weight = 2
    waiting_cost_weight = 5
    single_scene_weight = 1
    include_penalty_weight = 1
    avoid_penalty_weight = 3
    call_penalty_weight = 1

    total_cost = (time_cost*time_cost_weight + waiting_cost*waiting_cost_weight + single_scene_penalty *
                  single_scene_weight + include_penalty*include_penalty_weight + avoid_penalty*avoid_penalty_weight + call_penalty*call_penalty_weight)/(time_cost_weight+waiting_cost_weight + single_scene_weight + include_penalty_weight + avoid_penalty_weight + call_penalty_weight)
    if total_cost < 0:
        print('|---------------------------|')
        # print(proposal)
        print('time cost', time_cost*time_cost_weight)
        print('waiting cost', waiting_cost*waiting_cost_weight)
        print('single scene penalty', single_scene_penalty*single_scene_weight)
        print('include penalty', include_penalty*include_penalty_weight)
        print('avoid penalty', avoid_penalty*avoid_penalty_weight)
        print('call penalty', call_penalty*call_penalty_weight)

    return(total_cost, time_cost, waiting_cost)


def minimize(t_max, t_min, step_max,
             max_hours, min_hours, begin_state, sa_matrix,
             scene_time, actors_to_ignore, scenes_to_include, scenes_to_avoid):

    current_state = begin_state
    t = t_max
    current_energy, _, _ = cost(
        current_state, max_hours, min_hours, sa_matrix, scene_time, actors_to_ignore, scenes_to_include, scenes_to_avoid)
    best_state = current_state.copy()
    best_energy = current_energy
    hist = []

    step, accept = 1, 0
    while step <= step_max and t >= t_min and t > 0:

        # get proposed neighbor
        proposed_neighbor = get_neighbors(
            current_state, sa_matrix.shape[1], sa_matrix.shape[0])

        # check energy level of neighbor (we want to minimize energy)
        e_n, time, wait = cost(proposed_neighbor, max_hours, min_hours,
                               sa_matrix, scene_time, actors_to_ignore, scenes_to_include, scenes_to_avoid)
        dE = e_n - current_energy

        # determine if we should accept the current neighbor
        if random() < safe_exp(-dE / t):
            current_energy = e_n
            current_state = proposed_neighbor
            accept += 1

        # check if the current neighbor is best solution so far
        if e_n < best_energy:
            best_energy = e_n
            best_state = proposed_neighbor

        hist.append([step, t, best_energy, current_energy,
                    time, wait, current_state])

        # update temp
        t = update_t(step, t_min, t_max, step_max)
        step += 1

    return best_state, best_energy, hist


def load_data(path_to_csv):
    # load data
    # M x N matrix with M scenes and N actors,
    # where a value of 1 means actor is in the scene and 0 actor is NOT in the scene.
    sa_matrix = pd.read_csv(path_to_csv)
    sa_matrix.fillna(0, inplace=True)

    times = sa_matrix.iloc[:,[0]]
    times = np.array(times)
    times = [time[0] for time in times]

    sa_matrix = sa_matrix.iloc[: , 1:]
    names = list(sa_matrix.columns)
    names = [name.lower() for name in names]

    sa_matrix = sa_matrix.to_numpy()

    # matrix with actor does not have to show up for optional scene
    #sa_matrix_optional = pd.read_csv('scene-actor-matrix-optional.csv')
    #sa_matrix_optional.fillna(0, inplace=True)
    #sa_matrix_optional = sa_matrix_optional.to_numpy()

    return sa_matrix, names, times


def make_schedule(max_hours, min_hours, sa_matrix, scene_time, actors_to_ignore, scenes_to_include, scenes_to_avoid, max_cost):

    t_max = 105
    t_min = 0
    step_max = 1000

    # initial state (cannot contain scenes to avoid, or be empty)
    best_energy = 9999
    start_time = time.time()
    runtime = 0
    # max runtime before throwing error
    max_runtime = 30
    # run and if score is bad rerun automatically
    while best_energy > max_cost and runtime < max_runtime: 
        runtime = time.time()-start_time
        best_state = [1, 2, 3, 4, 5]
        print('starting run; start energy = ', best_energy)
        print('runtime = ', runtime)

        best_state, best_energy, hist = minimize(
            t_max, t_min, step_max, max_hours, min_hours, best_state, sa_matrix, scene_time, actors_to_ignore, scenes_to_include, scenes_to_avoid)

    if runtime > max_runtime:
        print('No good solution found in time, please try again', best_energy)
    else:
        print('Found solution with cost:', best_energy)

    return best_state, best_energy

