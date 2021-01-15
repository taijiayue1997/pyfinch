from analysis.functions import *
from analysis.parameters import *
import scipy
from scipy import spatial
from scipy.io import wavfile
from scipy.stats import sem
from matplotlib.pylab import psd
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from pathlib import Path
import pandas as pd
import seaborn as sns
from util.functions import *
from util.spect import *
from util.draw import *
from util import save
import json

# "birdID": ["g20r5", "y58y59", "k71o7", "y3y18", "o54w8", "k77r57", "b86g86"],

# Parameters
font_size = 12  # figure font size
note_buffer = 10  # in ms before and after each note

num_note_crit_basis = 30  # the number of basis note should be >= this criteria
num_note_crit_testing = 10  # the number of testing syllables should be >= this criteria
fig_save_ok = False
save_ok = False


def get_basis_psd(psd_array, notes):
    # Get avg psd from the training set (will serve as a basis)
    psd_dict = {}
    psd_basis_list = []
    syl_basis_list = []

    unique_note = unique(notes)  # convert note string into a list of unique syllables

    # Remove unidentifiable note (e.g., '0' or 'x')
    if '0' in unique_note:
        unique_note.remove('0')
    if 'x' in unique_note:
        unique_note.remove('x')

    for note in unique_note:
        ind = find_str(notes, note)
        if len(ind) >= num_note_crit_basis:  # number should exceed the  criteria
            syl_pow_array = psd_array[ind, :]
            syl_pow_avg = syl_pow_array.mean(axis=0)
            temp_dict = {note: syl_pow_avg}
            psd_basis_list.append(syl_pow_avg)
            syl_basis_list.append(note)
            psd_dict.update(temp_dict)  # basis
            # plt.plot(psd_dict[note])
            # plt.show()
    return psd_basis_list, syl_basis_list


# Obtain basis data from training files
def get_psd_mat(data_path, save_fig=False, nfft=2 ** 10):
    file_name = data_path / 'PSD.npy'

    # Read from a file if it already exists
    if file_name.exists():
        data = np.load(file_name, allow_pickle=True).item()
        psd_array, psd_list, all_notes = data['psd_array'], data['psd_list'], data['all_notes']
    else:

        # Load files
        files = list(data_path.glob('*.wav'))
        # files = files[:10]

        psd_list = []  # store psd vectors for training
        all_notes = ''  # concatenate all syllables

        for file in files:

            notmat_file = file.with_suffix('.wav.not.mat')
            onsets, offsets, intervals, durations, syllables, contexts = read_not_mat(notmat_file, unit='ms')
            sample_rate, data = wavfile.read(file)  # note that the timestamp is in second
            length = data.shape[0] / sample_rate
            timestamp = np.round(np.linspace(0, length, data.shape[0]) * 1E3,
                                 3)  # start from t = 0 in ms, reduce floating precision
            list_zip = zip(onsets, offsets, syllables)

            for i, (onset, offset, syllable) in enumerate(list_zip):

                # Get spectrogram
                ind, _ = extract_ind(timestamp, [onset - note_buffer, offset + note_buffer])
                extracted_data = data[ind]
                spect, freqbins, timebins = spectrogram(extracted_data, sample_rate, freq_range=freq_range)

                # Get power spectral density
                # nfft = int(round(2 ** 14 / 32000.0 * sample_rate))  # used by Dave Mets

                # Get psd after normalization
                psd_seg = psd(normalize(extracted_data), NFFT=nfft, Fs=sample_rate)  # PSD segment from the time range
                seg_start = int(round(freq_range[0] / (sample_rate / float(nfft))))  # 307
                seg_end = int(round(freq_range[1] / (sample_rate / float(nfft))))  # 8192
                psd_power = normalize(psd_seg[0][seg_start:seg_end])
                psd_freq = psd_seg[1][seg_start:seg_end]

                if save_fig:
                    # Plot spectrogram & PSD
                    fig = plt.figure(figsize=(3.5, 3))
                    fig_name = "{}, note#{} - {}".format(file.name, i, syllable)
                    fig.suptitle(fig_name, y=0.95)
                    gs = gridspec.GridSpec(6, 3)

                    # Plot spectrogram
                    ax_spect = plt.subplot(gs[1:5, 0:2])
                    ax_spect.pcolormesh(timebins * 1E3, freqbins, spect,  # data
                                        cmap='hot_r',
                                        norm=colors.SymLogNorm(linthresh=0.05,
                                                               linscale=0.03,
                                                               vmin=0.5,
                                                               vmax=100
                                                               ))

                    remove_right_top(ax_spect)
                    ax_spect.set_ylim(freq_range[0], freq_range[1])
                    ax_spect.set_xlabel('Time (ms)', fontsize=font_size)
                    ax_spect.set_ylabel('Frequency (Hz)', fontsize=font_size)

                    # Plot psd
                    ax_psd = plt.subplot(gs[1:5, 2], sharey=ax_spect)
                    ax_psd.plot(psd_power, psd_freq, 'k')

                    ax_psd.spines['right'].set_visible(False), ax_psd.spines['top'].set_visible(False)
                    ax_psd.spines['bottom'].set_visible(False)
                    ax_psd.set_xticks([])  # remove xticks
                    plt.setp(ax_psd.set_yticks([]))
                    # plt.show()

                    # Save figure
                    if fig_save_ok:
                        save_path = save.make_dir(file.parent, 'Spectrograms')
                        save.save_fig(fig, save_path, fig_name, ext='.png')

                all_notes += syllable
                psd_list.append(psd_power)

        psd_array = np.asarray(psd_list)  # number of syllables x psd

        # Organize data into a dictionary
        data = {
            'psd_array': psd_array,
            'psd_list': psd_list,
            'all_notes': all_notes,
        }
        # Save results
        np.save(file_name, data)

    return psd_array, psd_list, all_notes


# Store results in the dataframe
df = pd.DataFrame()
df_x = pd.DataFrame()
df_sig_prob = pd.DataFrame()  # dataframe for significant syllables

# Data path (Read from .json config file)
config_file = 'config.json'
with open(config_file, 'r') as f:
    config = json.load(f)

project_path = Path(config['project_dir'])

for bird in config['birdID']:

    training_path = ''

    for session in config['sessions']:

        testing_path = ''
        condition = ''

        data_path = project_path / bird / session

        if session == "pre-control1":
            training_path = data_path
            # print(f"training path = {training_path}")
        else:
            testing_path = data_path
            # print(f"testing path = {testing_path}")

        if training_path and testing_path:
            if training_path.name == "pre-control1" and testing_path.name == "pre-control2":
                condition = 'baseline'
            elif training_path.name == "pre-control1" and testing_path.name == "BMI":
                condition = 'BMI'

        if condition:
            print(f"training path = {training_path}")
            print(f"testing path = {testing_path}")
            print(condition)
            print("")

            # Obtain basis data from training files
            psd_array_training, psd_list_training, notes_training = get_psd_mat(training_path, save_fig=False)

            # Get basis psds per note
            psd_basis_list, note_basis_list = get_basis_psd(psd_array_training, notes_training)

            # Get psd from the testing set
            psd_array_testing, psd_testing_list, notes_testing = get_psd_mat(testing_path, save_fig=False)

            # Get similarity per syllable
            # Get psd distance
            distance = scipy.spatial.distance.cdist(psd_testing_list, psd_basis_list,
                                                    'sqeuclidean')  # (number of test notes x number of basis notes)

            # Convert to similarity matrices
            similarity = 1 - (distance / np.max(distance))  # (number of test notes x number of basis notes)

            # Plot similarity matrix per syllable
            note_testing_list = unique(notes_testing)  # convert syllable string into a list of unique syllables

            # Remove non-syllables (e.g., '0')
            if '0' in note_testing_list:
                note_testing_list.remove('0')
            if condition == 'control' and 'x' in note_testing_list:  # remove 'x' if it appears in the control data
                note_testing_list.remove('x')

            # Get similarity matrix per test note
            for note in note_testing_list:

                if note not in note_basis_list and note != 'x':
                    continue

                fig = plt.figure(figsize=(5, 5))
                # title = "Sim matrix: note = {}".format(note)
                fig_name = f"note - {note}"
                gs = gridspec.GridSpec(7, 8)

                ax = plt.subplot(gs[0:5, 1:7])
                ind = find_str(notes_testing, note)
                note_similarity = similarity[ind, :]  # number of the test notes x basis note
                nb_note = len(ind)

                if nb_note < num_note_crit_testing:
                    continue

                title = f"Sim matrix: note = {note} ({nb_note})"
                ax = sns.heatmap(note_similarity,
                                 vmin=0,
                                 vmax=1,
                                 cmap='binary')
                ax.set_title(title)
                ax.set_ylabel('Test syllables')
                ax.set_xticklabels(note_basis_list)
                plt.tick_params(left=False)
                plt.yticks([0.5, nb_note - 0.5], ['1', str(nb_note)])

                # Get mean or median similarity index
                ax = plt.subplot(gs[-1, 1:7], sharex=ax)
                similarity_mean = np.expand_dims(np.mean(note_similarity, axis=0), axis=0)  # or axis=1
                similarity_sem = sem(note_similarity, ddof=1)
                similarity_median = np.expand_dims(np.median(note_similarity, axis=0), axis=0)  # or axis=1

                ax = sns.heatmap(similarity_mean, annot=True, cmap='binary', vmin=0, vmax=1, annot_kws={"fontsize": 7})
                ax.set_xlabel('Basis syllables')
                ax.set_yticks([])
                ax.set_xticklabels(note_basis_list)
                # plt.show()

                if note is 'x':  # get the max if 'x'
                    similarity_mean_val = np.max(similarity_mean[0])
                    similarity_median_val = np.max(similarity_median[0])
                else:  # get the value from the matching note
                    similarity_mean_val = similarity_mean[0][note_basis_list.index(note)]
                    similarity_median_val = similarity_median[0][note_basis_list.index(note)]

                #TODO: Get entropy & softmax prob

                # Save figure
                if fig_save_ok:
                    save_path = save.make_dir(testing_path, 'NoteSimilarity', add_date=True)
                    save.save_fig(fig, save_path, fig_name, ext='.png')

                # Save results to a dataframe
                # All notes
                temp_df = []
                temp_df = pd.DataFrame({'BirdID': bird,
                                        'Condition': condition,
                                        'Note': note,  # testing note
                                        'NoteX': note is 'x',
                                        'NbNotes': [nb_note],
                                        'SimilarityMean': [similarity_mean_val],
                                        'SimilarityMedian': [similarity_median_val]
                                        })
                df = df.append(temp_df, ignore_index=True)

                # 'x' in BMI condition only
                if condition == 'BMI' and note is 'x':  # store mean similarity values for 'x'
                    for ind, basis_note in enumerate(note_basis_list):
                        temp_df_x = []
                        temp_df_x = pd.DataFrame({'BirdID': bird,
                                                'BasisNote': basis_note,  # testing note
                                                'SimilarityMean': [similarity_mean[0][ind]],
                                                'SimilaritySEM': [similarity_sem[ind]],
                                                })
                        df_x = df_x.append(temp_df_x, ignore_index=True)



    # Calculate the proportion of 'x's that exceeds the mean value of the similarity matrix in the control condition

    new_df = df.groupby(['Condition'])['SimilarityMean'].mean().reset_index()
    new_df = new_df[new_df['Condition'] == 'baseline']

    # 'x' similarity matrix
    ind = find_str(notes_testing, 'x')
    if len(ind) < num_note_crit_testing:  # if there are not enough 'x's, skip
        continue
    x_similarity = similarity[ind, :]  # number of the test notes x basis note
    sim_basis_mean = new_df['SimilarityMean'].values
    prob_sig_notes = (x_similarity > sim_basis_mean[0]).sum() / x_similarity.size  # proportion of notes having a higher similarity index relative to the baseline (mean similarity ind from the control (pre1 vs. pre2)

    # Select the maximum note only
    # max_col = x_similarity[:, x_similarity.mean(axis=0).argmax()]
    # prob_sig_notes = (max_col > sim_basis_mean[0]).sum() / max_col.size  # proportion of notes having a higher similarity index relative to the baseline (mean similarity ind from the control (pre1 vs. pre2)

    # Save results to a dataframe
    # All notes
    temp_df = []
    temp_df = pd.DataFrame({'BirdID': bird,
                            'SigProportion': [prob_sig_notes],
                            })
    df_sig_prob = df_sig_prob.append(temp_df, ignore_index=True)


    # Plot x with
    frame_width = 2
    fig = plt.figure(figsize=(6, 3))
    title = f"{bird}_SimilarityMat(x) - SigProb = {round(prob_sig_notes,3)}"
    plt.suptitle(title, size=9)
    fig_name = f"{bird}_SimilarityMat(x)"
    gs = gridspec.GridSpec(8, 8)
    ax = plt.subplot(gs[1:7, 1:4])
    ax = sns.heatmap(x_similarity,
                     vmin=0,
                     vmax=1,
                     cmap='binary')

    ax.set_ylabel('Test syllables')
    ax.set_xticklabels(note_basis_list)
    plt.tick_params(left=False)
    plt.yticks([0.5, nb_note - 0.5], ['1', str(nb_note)])

    # Plot with a boolean mask (sig bins only)
    x_similarity[x_similarity < sim_basis_mean[0]] = np.nan  # replace non-sig values with nan

    ax = plt.subplot(gs[1:7, 5:8])
    ax = sns.heatmap(x_similarity,
                     vmin=0,
                     vmax=1,
                     cmap='binary')

    ax.axhline(y=0, color='k', linewidth=frame_width/4)
    ax.axhline(y=x_similarity.shape[0], color='k', linewidth=frame_width)
    ax.axvline(x=0, color='k', linewidth=frame_width/4)
    ax.axvline(x=x_similarity.shape[1], color='k', linewidth=frame_width)

    ax.set_xticklabels(note_basis_list)
    plt.tick_params(left=False)
    plt.yticks([0.5, nb_note - 0.5], ['1', str(nb_note)])
    # plt.show()
    # Save the figure
    save_path = save.make_dir(project_path / 'Results', 'SigProb', add_date=True)
    save.save_fig(fig, save_path, fig_name, ext='.png')

# Save to csv (sig proportion)
outputfile = project_path / 'Results' / 'SigProportion.csv'
df_sig_prob.to_csv(outputfile, index=True, header=True)  # save the dataframe to .cvs format




# Save to csv
if save_ok:
    df.index.name = 'Index'
    outputfile = project_path / 'Results' / 'SimilarityIndex.csv'
    df.to_csv(outputfile, index=True, header=True)  # save the dataframe to .cvs format

    df_x.index.name = 'Index'
    outputfile = project_path / 'Results' / 'NoteX.csv'
    df_x.to_csv(outputfile, index=True, header=True)  # save the dataframe to .cvs format

print('Done!')

