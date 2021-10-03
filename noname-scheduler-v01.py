from ctypes import string_at
from tkinter import *
from tkinter import messagebox
import pandas as pd
from make_schedule import load_data, make_schedule, get_actor_call_times

root = Tk()

root.title('NoName rehearsal scheduler V0.1')
root.geometry("2000x600")

input_frame = LabelFrame(root,padx=10, pady=10)

path_e = Entry(root, width=50)
path_e.insert(END,'scene-actor-matrix.csv')
path_l = Label(root, text='Path to .csv file of M scenes and N actors (Mandatory): ')
path_l.grid(row=1, column=0, pady=10, padx=5)
path_e.grid(row=1, column=1, pady=10, padx=5)

time_e = Entry(root, width=50)
time_e.insert(END,[30, 60, 20, 30, 10, 20, 30, 30, 60, 90, 30, 30, 30, 20, 60, 20, 30])
time_l = Label(root, text='Enter rehearsal time per scene (minutes) separated by space (Mandatory): ')
time_l.grid(row=4, column=0, pady=10, padx=5)
time_e.grid(row=4, column=1, pady=10, padx=5)

name_e = Entry(root, width=50)
name_e.insert(END, ['Todd','Giuliano','Zach','Salvador','Heini','Leben','Arnaud','Sophie','Maggie','Paulina','Dish','Sarah','Tom','Magdalena'])
name_l = Label(root, text='Enter actor\'s names separated by space (Mandatory): ')
name_l.grid(row=6, column=0, pady=10, padx=5)
name_e.grid(row=6, column=1, pady=10, padx=5)

actors_i_e = Entry(root, width=50)
actors_i_e.insert(END, [3,5])
actors_i_l = Label(root, text='Enter actor\'s number to ignore when calculating waiting time (optional) ')
actors_i_l.grid(row=10, column=0, pady=10, padx=5)
actors_i_e.grid(row=10, column=1, pady=10, padx=5)

scenes_a_e = Entry(root, width=50)
scenes_a_l = Label(root, text='Scenes to avoid (separated by whitespace, optional):')
scenes_a_l.grid(row=12, column=0, pady=10, padx=5)
scenes_a_e.grid(row=12, column=1, pady=10, padx=5)

scenes_i_e = Entry(root, width=50)
scenes_i_l = Label(root, text='Scenes to include (separated by whitespace, optional):')
scenes_i_l.grid(row=14, column=0, pady=10, padx=5)
scenes_i_e.grid(row=14, column=1, pady=10, padx=5)

min_e = Entry(root, width=50)
min_l = Label(root, text='Minimum number of hours to schedule (Mandatory):')
min_l.grid(row=16, column=0, pady=10, padx=5)
min_e.grid(row=16, column=1, pady=10, padx=5)

max_e = Entry(root, width=50)
max_l = Label(root, text='Maximum number of hours to schedule (Mandatory):')
max_l.grid(row=18, column=0, pady=10, padx=5)
max_e.grid(row=18, column=1, pady=10, padx=5)

def string_to_list(input_string, to_int = False):
    splt_string = input_string.strip()
    splt_string = str.split(splt_string, sep=' ')
    if to_int:
        if any(char.isdigit() for char in splt_string):
            splt_string = [int(i) for i in splt_string]
        else:
            return []

    return splt_string

def get_schedule_print(scene_matrix, name_list, scene_time, selected_scenes):
    scheduledf = pd.DataFrame(scene_matrix.T, index=name_list, columns=list(range(1,len(scene_time)+1)))
    scheduledf = scheduledf[selected_scenes]
    scheduledf.replace(0, ' ', inplace=True)
    scheduledf.replace(1, 'x', inplace=True)
    return scheduledf

def prepare_schedule():
    wait_label = Label(root, text='Calculating... This can take up to a minute', fg='red')
    wait_label.grid(row=24, column=0)

    try:
        path_to_csv = path_e.get().strip()
        scene_time = string_to_list(time_e.get(),True)
        actors_list = string_to_list(name_e.get(), False)
        actors_ignore = string_to_list(actors_i_e.get(), True)
        scenes_avoid = string_to_list(scenes_a_e.get(), True)
        scenes_include = string_to_list(scenes_i_e.get(), True)
        
        min_hours = float(min_e.get())
        max_hours = float(max_e.get())

        input_matrix = load_data(path_to_csv=path_to_csv)
        print(scene_time)
        print(actors_list)
        print(actors_ignore)
        print(scenes_include)
        print(scenes_avoid)
        print(min_hours)
        print(max_hours)
        print(input_matrix)

        best_state, best_energy = make_schedule(max_hours=max_hours, min_hours=min_hours, sa_matrix=input_matrix, scene_time=scene_time,
                    actors_to_ignore=actors_ignore, scenes_to_include=scenes_include, scenes_to_avoid=scenes_avoid)
    
    except:
        messagebox.showerror(title='ERROR', message='Something went wrong, are all the mandatory fields filled in?')
        wait_label.destroy()
        return

    call_times = get_actor_call_times(state=best_state, name_list=actors_list, scene_time=scene_time, sa_matrix=input_matrix)
    result_frame = LabelFrame(root, text='results', padx=50, pady=50)
    result_frame.grid(row=1, column=3, padx=20, pady=20, rowspan=25)
    call_times_l = Label(result_frame, text=str(call_times),wraplength=400)
    #call_times_l.grid(row=22, column=0)

    selected_scenes = [scene+1 for scene in best_state]
    selected_scenes_l = Label(result_frame, text='Suggested scene rehearsal order: '+ str(selected_scenes))
    best_energy_l = Label(result_frame, text= 'Quality of suggestion (lower=better): ' + str(best_energy))
    selected_scenes_l.grid(row=0, columnspan=10)
    best_energy_l.grid(row=1, columnspan=10)

    schedule_print = get_schedule_print(scene_matrix=input_matrix, name_list=actors_list, scene_time=scene_time, selected_scenes=selected_scenes)
    # scene number label starts or row 2 col 1
    for ix, scene in enumerate(selected_scenes):
        result_scenes_e = Label(result_frame, width=5, text=str(scene), justify=CENTER)
        result_scenes_e.grid(row=2, column=ix+1)
    # actor names label starts on row 4 col 0
    for ix, actor in enumerate(actors_list):
        result_actors_e = Label(result_frame, width=10, text=actor, justify=RIGHT)
        result_actors_e.grid(row=ix+3, column=0)

    for row_ix, row in schedule_print.iterrows():
        for col_ix, col in enumerate(row):
            x_or_not = Label(result_frame, width=5, text=col, justify=CENTER)
            x_or_not.grid(row=schedule_print.index.get_loc(row_ix)+3, column=col_ix+1)



    wait_label.destroy()

button_ms = Button(root, text='Make schedule', command=prepare_schedule, width=20)
button_ms.grid(row=20,column=0)




root.mainloop()

