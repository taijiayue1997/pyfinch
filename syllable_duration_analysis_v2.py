"""
By Jaerong (2020/06/04)
Syllable duration for all syllables regardless of it type
Calculation based on EventInfo.m
"""
from database import load
import pandas as pd
from song.analysis import *
from utilities import save


def get_data(query):
    """
    Input: SQL query
    calculate the syllable duration from .not.mat and store the data in .csv
    """
    global save_dir

    # Create save dir
    dir_name = 'SyllableDuration'
    save_dir = save.make_save_dir(dir_name, add_date=False)

    # Store results in the dataframe
    df = pd.DataFrame()

    # Load song database
    cur, conn, col_names = load.database(query)

    for song_info in cur.fetchall():
        song_name, song_path = load.song_info(song_info)
        print('\nAccessing... ' + song_name)

        for site in [x for x in song_path.iterdir() if x.is_dir()]:  # loop through different sites on the same day

            mat_files = [file for file in site.rglob('*.not.mat')]

            for file in mat_files:
                # Load variables from .not.mat
                print(file.name)
                # print(file)
                onsets, offsets, intervals, duration, syllables, context = \
                    read_not_mat(file)

                # Type of the syllables
                syl_type = syl_type_(syllables, song_info)

                nb_syllable = len(syllables)

                # Save results to a dataframe
                temp_df = []
                temp_df = pd.DataFrame({'SongID': [song_info['id']] * nb_syllable,
                                        'BirdID': [song_info['birdID']] * nb_syllable,
                                        'TaskName': [song_info['taskName']] * nb_syllable,
                                        'TaskSession': [song_info['taskSession']] * nb_syllable,
                                        'TaskSessionDeafening': [song_info['taskSessionDeafening']] * nb_syllable,
                                        'TaskSessionPostdeafening': [song_info[
                                                                         'taskSessionPostDeafening']] * nb_syllable,
                                        'DPH': [song_info['dph']] * nb_syllable,
                                        'Block10days': [song_info['block10days']] * nb_syllable,
                                        'FileID': [file.name] * nb_syllable,
                                        'Context': [context] * nb_syllable,
                                        'SyllableType': syl_type,
                                        'Syllable': list(syllables),
                                        'Duration': duration,
                                        })
                df = df.append(temp_df, ignore_index=True)

    # Save to a file
    df.index.name = 'Index'
    outputfile = save_dir / 'SyllableDuration.csv'
    df.to_csv(outputfile, index=True, header=True)  # save the dataframe to .cvs format
    print('Done!')


def load_data(data_file, context='ALL', syl_type='ALL'):

    df = pd.read_csv(data_file)

    # Select syllables based on social context
    if context is 'U':
        df = df.query('Context == "U"')  # select only Undir
    elif context is 'D':
        df = df.query('Context == "D"')  # select only Dir

    # Only select syllables of a particular type
    if syl_type is 'M':
        df = df.query('SyllableType == "M"')  # eliminate non-labeled syllables (e.g., 0)
    elif syl_type is 'C':
        df = df.query('SyllableType == "C"')  # eliminate non-labeled syllables (e.g., 0)
    elif syl_type is 'I':
        df = df.query('SyllableType == "I"')  # eliminate non-labeled syllables (e.g., 0)
    return df


if __name__ == '__main__':

    # Check if the data .csv exists
    project_path = load.project()
    data_file = project_path / 'Analysis' / 'SyllableDuration' / 'SyllableDuration.csv'

    if not data_file.exists():

        # Get the syllable duration data
        query = "SELECT * FROM song"
        # query = "SELECT * FROM song WHERE id BETWEEN 1 AND 16"
        get_data(query)
        df = load_data(data_file, context='ALL', syl_type='ALL')
    else:
        df = load_data(data_file, context='ALL', syl_type='ALL')


# Plot the results

import matplotlib.pyplot as plt
import seaborn as sns
import IPython
from utilities.functions import unique


bird_list = unique(df['BirdID'].tolist())
task_list = unique(df['TaskName'].tolist())

for bird in bird_list:

    for task in task_list:

        note_list = unique(df['Syllable'].tolist())

        # bird = 'b70r38'
        # task = 'Predeafening'

        temp_df = []
        temp_df = df.loc[(df['BirdID'] == bird) & (df['TaskName'] == task)]

        if temp_df.empty:
            continue

        note_list = unique(temp_df.query('SyllableType == "M"')['Syllable'])  # only motif syllables

        title = '-'.join([bird, task])
        fig = plt.figure(figsize=(6, 5))
        plt.suptitle(title, size=10)
        # ax = sns.distplot((temp_df['Duration'], hist= False, kde= True)
        ax = sns.kdeplot(temp_df['Duration'], bw=0.05, label='', color='k', linewidth=2)
        # kde = zip(ax.get_lines()[0].get_data()[0], ax.get_lines()[0].get_data()[1])
        # sns.rugplot(temp_df['Duration'])  # shows ticks

        # https: // stackoverflow.com / questions / 43565892 / python - seaborn - distplot - y - value - corresponding - to - a - given - x - value
        # TODO: extrapolate value and mark with an arrow

        # mark each note
        median_dur = list(zip(note_list, temp_df.query('SyllableType == "M"').groupby(['Syllable'])[
            'Duration'].mean().to_list()))  # [('a', 236.3033654971783), ('b', 46.64262295081962), ('c', 154.57333333333335), ('d', 114.20039483457349)]
        for note, dur in median_dur:
            plt.axvline(dur, color='k', linestyle='dashed', linewidth=1)
            plt.arrow(dur, 5, 0, -1)
        ax.spines['right'].set_visible(False), ax.spines['top'].set_visible(False)
        plt.xlabel('Duration (ms)')
        plt.ylabel('Probability Density')
        # plt.xlim(0, ceil(max(df.loc[(df['BirdID'] == bird)]['Duration']) / 100) * 100)
        plt.xlim(0, 300)
        plt.ylim(0, 0.06)

        # print('Prcessing... {} from Bird {}'.format(task, bird))

        # Save results
        save_dir = project_path / 'Analysis' / 'SyllableDuration'
        save.figure(fig, save_dir, title, ext='.png')
    # IPython.embed()
    #     break
    # break
print('Done!')
