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


# This function is correct.
def get_actor_call_times(state, name_list, scene_time, sa_matrix):
    # get what the first scene is when people need to attend
    n_actors = len(name_list)
    nr_calls = [0]*len(state)
    actor_call_time = [None]*n_actors
    
    # Loop over all actors
    for actor_ix, actor in enumerate(sa_matrix.T):
        actor_id = actor_ix + 1
        
        attend = actor[state]
        for i in range(1, len(attend)+1):
            call_slice = attend[0:i]
            call_test = (i-1)*[0]+[1]

            if (call_slice == call_test).all():
                actor_call_time[actor_ix] = i
                nr_calls[i-1] += 1

    # get info in nice dict form
    call_time_dict = {}

    temp = np.array(scene_time)
    len_state_scenes = list(temp[state])
    for ix, call_scene in enumerate(actor_call_time):
        if call_scene:
            call_time_dict[name_list[ix]] = sum(len_state_scenes[0:call_scene-1])

    return call_time_dict, nr_calls


# --- THIS FUNCTION CONTAINS THE PENALTY FIX ---
def energy_function(state, sa_matrix, scene_time, max_hours, min_hours, actors_to_ignore, name_list, scenes_to_avoid_0idx):
    
    temp = np.array(scene_time)
    len_state_scenes = list(temp[state])
    total_time = sum(len_state_scenes) 

    # --- Actor Hard Constraint Penalty (Renamed for clarity) ---
    actor_hard_constraint_penalty = 0
    if actors_to_ignore: 
        try:
            actors_to_ignore_0idx = [a - 1 for a in actors_to_ignore]
            state_matrix = sa_matrix[state, :]
            state_ignored_actor_matrix = state_matrix[:, actors_to_ignore_0idx]
            violations = np.sum(state_ignored_actor_matrix)
            actor_hard_constraint_penalty = violations * 1000000 
        except IndexError:
            actor_hard_constraint_penalty = 1000000 
            print("Warning: Index error during hard constraint check.")

    # --- THIS IS THE FIX: Add Avoided Scene Penalty ---
    avoided_scene_penalty = 0
    # Check if state is not empty (no scenes, no violations)
    if scenes_to_avoid_0idx and state: 
        avoided_scene_violations = set(state) & set(scenes_to_avoid_0idx)
        avoided_scene_penalty = len(avoided_scene_violations) * 1000000
    # --- END OF FIX ---
            
    # --- Time Constraint Penalty (Unchanged) ---
    max_time = max_hours*60
    min_time = min_hours*60
    time_constraint_penalty = 0
    
    if total_time > max_time:
        time_constraint_penalty = 1000 * (total_time - max_time)
    if total_time < min_time:
        time_constraint_penalty = 1000 * (min_time - total_time)
        
    # --- Update Breakdown Dict ---
    energy_breakdown = {
        "Total Time (min)": total_time,
        "Wait Time (min)": 0,
        "Call Penalty": 0,
        "Short Work Penalty": 0, 
        "Time Constraint Penalty": time_constraint_penalty,
        "Actor Ignore Penalty": actor_hard_constraint_penalty, # Renamed
        "Avoided Scene Penalty": avoided_scene_penalty # Added
    }
    
    if not state:
        base_energy = 999999 + time_constraint_penalty + actor_hard_constraint_penalty + avoided_scene_penalty
        return base_energy, {}, [0], energy_breakdown

    # --- 1. Corrected Wait Time Logic & Short Work Penalty (Unchanged) ---
    total_wait_time = 0
    short_work_penalty = 0 
    n_actors = sa_matrix.shape[1] 
    state_matrix = sa_matrix[state, :]
    
    for actor_ix in range(n_actors):
        if (actor_ix + 1) in actors_to_ignore:
             continue
             
        actor_schedule_in_state = state_matrix[:, actor_ix]
        scenes_present_indices = np.where(actor_schedule_in_state == 1)[0]
        
        if len(scenes_present_indices) == 0:
            continue
            
        first_scene_pos = scenes_present_indices[0]
        last_scene_pos = scenes_present_indices[-1]
        
        actor_schedule_slice_durations = len_state_scenes[first_scene_pos : last_scene_pos + 1]
        actor_schedule_in_state_slice = actor_schedule_in_state[first_scene_pos : last_scene_pos + 1]
        
        total_actor_time_min = sum(actor_schedule_slice_durations)
        actor_work_time_min = sum(np.array(actor_schedule_slice_durations) * actor_schedule_in_state_slice)
        
        wait_time = total_actor_time_min - actor_work_time_min
        total_wait_time += wait_time
        
        if actor_work_time_min > 0 and actor_work_time_min < 60:
            short_work_penalty += 500 
        
    # --- 2. Call Time / Nr_Calls Calculation (Unchanged) ---
    call_times, nr_calls = get_actor_call_times(state, name_list, scene_time, sa_matrix)

    # --- 3. Combined Energy Calculation ---
    call_penalty = sum(nr_calls) * 50 
    
    total_energy = (total_wait_time + call_penalty + time_constraint_penalty + 
                    actor_hard_constraint_penalty + avoided_scene_penalty + short_work_penalty)
    
    # --- Update Final Breakdown Dict ---
    energy_breakdown = {
        "Total Time (min)": total_time,
        "Wait Time (min)": total_wait_time,
        "Call Penalty": call_penalty,
        "Short Work Penalty": short_work_penalty, 
        "Time Constraint Penalty": time_constraint_penalty,
        "Actor Ignore Penalty": actor_hard_constraint_penalty, # Renamed
        "Avoided Scene Penalty": avoided_scene_penalty # Added
    }
    
    return total_energy, call_times, nr_calls, energy_breakdown


# --- THIS FUNCTION CONTAINS THE INDEXING FIX ---
def get_neighbour(state, scenes_to_avoid_0idx, scenes_to_include_0idx, sa_matrix):
    # get a random neighbour state
    # by adding, removing or swapping a scene
    
    n_scenes = len(sa_matrix)
    new_state = state[:]
    
    # 50% chance to add/remove, 50% chance to swap
    if random() < 0.5 or len(new_state) < 2:
        # add or remove
        add = True
        if not new_state: # if empty, must add
            add = True
        elif len(new_state) >= n_scenes: # if full, must remove
            add = False
        elif random() < 0.5: # 50/50
            add = False
            
        if add:
            # Add a scene
            # --- FIX: Use 0-indexed scenes_to_avoid_0idx ---
            possible_scenes = list(set(range(n_scenes)) - set(new_state) - set(scenes_to_avoid_0idx))
            if not possible_scenes:
                return new_state # No scenes left to add
            
            scene_to_add = possible_scenes[randint(0, len(possible_scenes) - 1)]
            
            if new_state:
                insert_pos = randint(0, len(new_state))
                new_state.insert(insert_pos, scene_to_add)
            else:
                new_state.append(scene_to_add)
        else:
            # Remove a scene
            # Do not remove scenes that are in the "must include" list
            possible_removals = []
            for ix, scene in enumerate(new_state):
                # --- FIX: Use 0-indexed scenes_to_include_0idx ---
                # scene is 0-indexed, check against 0-indexed list
                if scene not in scenes_to_include_0idx:
                    possible_removals.append(ix)
            
            if not possible_removals:
                # This can happen if state is only "must_include" scenes
                if len(new_state) > 1:
                    idx1, idx2 = np.random.choice(len(new_state), 2, replace=False)
                    new_state[idx1], new_state[idx2] = new_state[idx2], new_state[idx1]
                return new_state # Return (potentially swapped) state
                
            remove_pos = possible_removals[randint(0, len(possible_removals) - 1)]
            new_state.pop(remove_pos)
            
    else:
        # swap
        if len(new_state) > 1:
            idx1, idx2 = np.random.choice(len(new_state), 2, replace=False)
            new_state[idx1], new_state[idx2] = new_state[idx2], new_state[idx1]

    return new_state


def load_data(path_to_csv):
    """Loads all data from the CSV."""
    try:
        df = pd.read_csv(path_to_csv, index_col=0, header=0)
        
        # Fill all empty cells (read as NaN) with 0 before converting
        df_filled = df.fillna(0)
        
        # Get actor names from columns
        actor_names = list(df_filled.columns)
        
        # Get scene times from index (the first column)
        scene_times = list(df_filled.index.values)
        
        # Get the matrix as numpy array
        sa_matrix = df_filled.to_numpy().astype(int)
        
        # Ensure scene_times are numbers
        try:
            scene_times_numeric = [int(t) for t in scene_times]
        except ValueError:
            raise ValueError("The first column (scene times/index) contains non-numeric values.")
        
        return sa_matrix, actor_names, scene_times_numeric
        
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path_to_csv}")
    except pd.errors.EmptyDataError:
        raise ValueError("The CSV file is in empty.")
    except Exception as e:
        raise ValueError(f"Error reading CSV: {e}. Ensure it has a header (actor names) and an index col (scene times).")


# --- THIS FUNCTION CONTAINS THE INDEXING FIX ---
def make_schedule(max_hours, min_hours, sa_matrix, scene_time, actors_list, actors_to_ignore, scenes_to_include, scenes_to_avoid):

    t_max = 105
    t_min = 0
    step_max = 10000

    # --- THIS IS THE FIX ---
    # Convert 1-based UI lists to 0-based algorithm lists
    n_scenes_total = len(sa_matrix)
    scenes_to_include_0idx = [s - 1 for s in scenes_to_include if s - 1 < n_scenes_total]
    scenes_to_avoid_0idx = [s - 1 for s in scenes_to_avoid if s - 1 < n_scenes_total]
    # --- END OF FIX ---

    # --- FIX: Use 0-indexed lists for start_state ---
    start_state = [scene for scene in scenes_to_include_0idx if scene not in scenes_to_avoid_0idx]
    start_state = list(set(start_state)) # Remove duplicates
    
    if not start_state:
        # If no scenes to include, start with a random valid scene
        possible_starts = list(set(range(n_scenes_total)) - set(scenes_to_avoid_0idx))
        if possible_starts:
            start_state = [possible_starts[randint(0, len(possible_starts)-1)]]
        else:
            start_state = [0] # Fallback
    # --- END OF FIX ---
            
    best_state = start_state
    
    # --- FIX: Pass 0-indexed list to energy_function ---
    E_old, best_call_times, best_nr_calls, best_breakdown = energy_function(best_state, sa_matrix, scene_time, max_hours, min_hours, actors_to_ignore, actors_list, scenes_to_avoid_0idx)
    best_energy = E_old
    
    for step in range(0, step_max):
        t = update_t(step, t_min, t_max, step_max)

        # --- FIX: Pass 0-indexed lists to get_neighbour ---
        new_state = get_neighbour(best_state, scenes_to_avoid_0idx, scenes_to_include_0idx, sa_matrix)
        
        # --- FIX: Pass 0-indexed list to energy_function ---
        E_new, new_call_times, new_nr_calls, new_breakdown = energy_function(new_state, sa_matrix, scene_time, max_hours, min_hours, actors_to_ignore, actors_list, scenes_to_avoid_0idx)
        
        delta_e = E_new - E_old

        if delta_e < 0:
            best_state = new_state
            best_energy = E_new
            E_old = E_new
            best_call_times = new_call_times
            best_nr_calls = new_nr_calls
            best_breakdown = new_breakdown
        else:
            if safe_exp(-delta_e/t) > random():
                best_state = new_state
                E_old = E_new
                
    # Check if final state has hard constraint violations
    if best_energy >= 1000000:
        print("Warning: Could not find a valid schedule. The one found violates a hard constraint.")
    
    # --- FIX: Check 0-indexed list ---
    for scene_to_include_0 in scenes_to_include_0idx:
        if scene_to_include_0 not in best_state:
            # Convert back to 1-based for the warning
            print(f"Warning: Could not include scene {scene_to_include_0 + 1} in final schedule.")
    # --- END OF FIX ---

    return best_state, best_energy, best_call_times, best_nr_calls, best_breakdown


# --- THIS FUNCTION IS CORRECT ---
def get_schedule_print(scene_matrix, name_list, scene_time, selected_scenes, actors_to_ignore=[]):
    
    # Handle empty schedule case
    if not selected_scenes:
        schedule_df = pd.DataFrame(index=name_list)
        schedule_df['Wait (min)'] = 0
        schedule_df['Total (min)'] = 0
        if actors_to_ignore:
            actors_to_ignore_0idx = [a - 1 for a in actors_to_ignore]
            names_to_drop = [name_list[i] for i in actors_to_ignore_0idx if i < len(name_list)]
            schedule_df = schedule_df.drop(names_to_drop, errors='ignore')
        
        schedule_df = schedule_df[schedule_df['Total (min)'] > 0]
        return schedule_df

    # --- Schedule is NOT empty, proceed ---
    selected_scenes_1indexed = [s + 1 for s in selected_scenes]
    schedule_matrix = scene_matrix[selected_scenes, :]
    
    schedule_df = pd.DataFrame(schedule_matrix.T, columns=selected_scenes_1indexed, index=name_list)
    schedule_df_display = schedule_df.replace({1: 'X', 0: ''})
    
    scene_times_np = np.array(scene_time)[selected_scenes]
    scene_duration_map = pd.Series(scene_times_np, index=schedule_df.columns)

    wait_times = []
    total_times = []
    
    for actor_name, row in schedule_df.iterrows():
        actor_scenes = row[row == 1]
        
        if actor_scenes.empty:
            wait_times.append(0)
            total_times.append(0)
            continue
            
        actor_scene_indices = actor_scenes.index
        
        schedule_cols_list = list(schedule_df.columns)
        first_scene_pos = schedule_cols_list.index(actor_scene_indices[0])
        last_scene_pos = schedule_cols_list.index(actor_scene_indices[-1])
        
        actor_schedule_slice_durations = scene_times_np[first_scene_pos : last_scene_pos + 1]
        
        actor_total_time_min = np.sum(actor_schedule_slice_durations)
        actor_work_time_min = scene_duration_map[actor_scene_indices].sum()
        wait_time = actor_total_time_min - actor_work_time_min
        
        wait_times.append(int(wait_time))
        total_times.append(int(actor_total_time_min))

    schedule_df_display['Wait (min)'] = wait_times
    schedule_df_display['Total (min)'] = total_times
    
    # Drop IGNORED actors
    if actors_to_ignore:
        actors_to_ignore_0idx = [a - 1 for a in actors_to_ignore]
        names_to_drop = [name_list[i] for i in actors_to_ignore_0idx if i < len(name_list)]
        schedule_df_display = schedule_df_display.drop(names_to_drop, errors='ignore')

    # Drop UNCALLED actors
    schedule_df_display = schedule_df_display[schedule_df_display['Total (min)'] > 0]

    return schedule_df_display