# Practice creating an audio object

from database.load import ProjectLoader
from analysis.spike import *
from analysis.parameters import *
from pathlib import Path
from analysis.load import read_rhd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.gridspec as gridspec
from util import save
from util.spect import *
from util.draw import *
from scipy.ndimage import gaussian_filter1d


# Select statement
query = "SELECT * FROM cluster WHERE id == 96"

project = ProjectLoader()
cur, conn, col_names = project.load_db(query)

# Figure parameters
rec_yloc = 0.05
rec_height = 1  # syllable duration rect
text_yloc = 0.5  # text height
font_size = 10
update=False

# Loop through neurons
for row in cur.fetchall():

    # ci = ClusterInfo(row, update=False)
    mi = MotifInfo(row, update=True)

    # Plot spectrogram & peri-event histogram (Just the first rendition)
    # for onset, offset in zip(mi.onsets, mi.offsets):
    onset = mi.onsets[0]
    offset = mi.offsets[0]

    # Convert from string to array of floats
    onset = np.asarray(list(map(float, onset)))
    offset = np.asarray(list(map(float, offset)))

    # Motif start and end
    start = onset[0] - peth_parm['buffer']
    end = offset[-1] + peth_parm['buffer']
    duration = offset[-1] - onset[0]

    # Get spectrogram
    audio = AudioData(row).extract([start, end])
    audio.spectrogram(freq_range=freq_range)

    # Plot figure
    fig = plt.figure(figsize=(5.5,9))
    plt.suptitle(mi.name, y=.95)
    gs = gridspec.GridSpec(18, 1)
    gs.update(wspace=0.025, hspace=0.05)

    # Plot spectrogram
    ax_spect = plt.subplot(gs[1:3])
    ax_spect.pcolormesh(audio.timebins * 1E3 - peth_parm['buffer'], audio.freqbins, audio.spect,  # data
                        cmap='hot_r',
                        norm=colors.SymLogNorm(linthresh=0.05,
                                               linscale=0.03,
                                               vmin=0.5,
                                               vmax=100
                                               ))

    remove_right_top(ax_spect)
    ax_spect.set_xlim(-peth_parm['buffer'], duration + peth_parm['buffer'])
    ax_spect.set_ylim(freq_range[0], freq_range[1])
    ax_spect.set_ylabel('Frequency (Hz)', fontsize=font_size)
    plt.yticks(freq_range, [str(freq_range[0]), str(freq_range[1])])
    # ax_spect.set_xlabel('Time (ms)', fontsize=font_size)

    # Plot syllable duration
    ax_syl = plt.subplot(gs[0], sharex= ax_spect)
    note_dur = offset - onset  # syllable duration
    onset -= onset[0]  # start from 0
    offset = onset + note_dur

    # Mark syllables
    for i, syl in enumerate(mi.motif):
        rectangle = plt.Rectangle((onset[i], rec_yloc), note_dur[i], 0.2,
                                  linewidth=1, alpha = 0.5, edgecolor='k', facecolor=note_color['Motif'][i])
        ax_syl.add_patch(rectangle)
        ax_syl.text((onset[i] + (offset[i] - onset[i]) / 2), text_yloc, syl, size=font_size)
    ax_syl.axis('off')


    # Plot raster
    line_offsets = np.arange(0.5,len(mi))
    zipped_lists = zip(mi.contexts, mi.spk_ts_warp, mi.onsets)
    ax_raster = plt.subplot(gs[4:6], sharex= ax_spect)

    pre_context = ''  # for marking  context change
    context_change = np.array([])

    for motif_ind, (context, spk_ts_warp, onset) in enumerate(zipped_lists):

        # Plot rasters
        spk = spk_ts_warp - float(onset[0])
        # print(len(spk))
        # print("spk ={}, nb = {}".format(spk, len(spk)))
        # print('')
        ax_raster.eventplot(spk, colors='k', lineoffsets=line_offsets[motif_ind],
                     linelengths=1, orientation='horizontal')

        # Demarcate the note
        k = 1  # index for setting the motif color
        for i, dur in enumerate(mi.median_durations):

            if i == 0:
                # print("i is {}, color is {}".format(i, i-k))
                rectangle = plt.Rectangle((0, motif_ind), dur, rec_height,
                                          fill=True,
                                          linewidth=1,
                                          alpha=0.15,
                                          facecolor=note_color['Motif'][i])
            elif not i%2:
                # print("i is {}, color is {}".format(i, i-k))
                rectangle = plt.Rectangle((sum(mi.median_durations[:i]), motif_ind), mi.median_durations[i], rec_height,
                                          fill=True,
                                          linewidth=1,
                                          alpha=0.15,
                                          facecolor=note_color['Motif'][i - k])
                k += 1
            ax_raster.add_patch(rectangle)

        # Demarcate song block (undir vs dir) with a horizontal line
        if pre_context != context:

            ax_raster.axhline(y=motif_ind-1, color='k', ls='-', lw=0.5)
            context_change = np.append(context_change, (motif_ind))
            if pre_context:
                ax_raster.text(ax_raster.get_xlim()[1] + 0.2,
                               ((context_change[-1] - context_change[-2]) / 3) + context_change[-2],
                               pre_context,
                               size=6)

        pre_context = context
    # Demarcate the last block
    ax_raster.text(ax_raster.get_xlim()[1] + 0.2,
                   ((ax_raster.get_ylim()[1] - context_change[-1]) / 3) + context_change[-1],
                   pre_context,
                   size=6)

    ax_raster.set_ylim(0,len(mi))
    ax_raster.set_ylabel('Trial #', fontsize=font_size)
    # ax_raster.set_xlabel('Time (ms)', fontsize=font_size)
    plt.yticks([0, len(mi)], [str(0), str(len(mi))])
    remove_right_top(ax_raster)
    ax_raster.set_xticks([])  # remove xticks


    # Plot sorted raster
    ax_raster = plt.subplot(gs[7:9], sharex= ax_spect)
    line_offsets = np.arange(0.5,len(mi))

    # Sort trials based on context
    sort_ind = np.array([i[0] for i in sorted(enumerate(mi.contexts), key=lambda x: x[1], reverse=True)])
    mi.contexts_sorted = np.array(mi.contexts)[sort_ind].tolist()
    mi.spk_ts_warp_sorted = np.array(mi.spk_ts_warp)[sort_ind].tolist()
    mi.onsets_sorted = np.array(mi.onsets)[sort_ind].tolist()

    zipped_lists = zip(mi.contexts_sorted, mi.spk_ts_warp_sorted, mi.onsets_sorted)

    pre_context = ''  # for marking  context change
    context_change = np.array([])

    for motif_ind, (context, spk_ts_warp, onset) in enumerate(zipped_lists):

        # Plot rasters
        spk = spk_ts_warp - float(onset[0])
        # print(len(spk))
        # print("spk ={}, nb = {}".format(spk, len(spk)))
        # print('')
        ax_raster.eventplot(spk, colors='k', lineoffsets=line_offsets[motif_ind],
                     linelengths=1, orientation='horizontal')

        # Demarcate the note
        k = 1  # index for setting the motif color
        for i, dur in enumerate(mi.median_durations):

            if i == 0:
                # print("i is {}, color is {}".format(i, i-k))
                rectangle = plt.Rectangle((0, motif_ind), dur, rec_height,
                                          fill=True,
                                          linewidth=1,
                                          alpha=0.15,
                                          facecolor=note_color['Motif'][i])
            elif not i%2:
                # print("i is {}, color is {}".format(i, i-k))
                rectangle = plt.Rectangle((sum(mi.median_durations[:i]), motif_ind), mi.median_durations[i], rec_height,
                                          fill=True,
                                          linewidth=1,
                                          alpha=0.15,
                                          facecolor=note_color['Motif'][i - k])
                k += 1
            ax_raster.add_patch(rectangle)

        # Demarcate song block (undir vs dir) with a horizontal line
        if pre_context != context:

            ax_raster.axhline(y=motif_ind-1, color='k', ls='-', lw=0.5)
            context_change = np.append(context_change, (motif_ind))
            if pre_context:
                ax_raster.text(ax_raster.get_xlim()[1] + 0.2,
                               ((context_change[-1] - context_change[-2]) / 3) + context_change[-2],
                               pre_context,
                               size=6)

        pre_context = context
    # Demarcate the last block
    ax_raster.text(ax_raster.get_xlim()[1] + 0.2,
                   ((ax_raster.get_ylim()[1] - context_change[-1]) / 3) + context_change[-1],
                   pre_context,
                   size=6)

    ax_raster.set_ylim(0,len(mi))
    ax_raster.set_ylabel('Trial #', fontsize=font_size)
    # ax_raster.set_xlabel('Time (ms)', fontsize=font_size)
    ax_raster.set_title('sorted raster', size=font_size)

    plt.yticks([0, len(mi)], [str(0), str(len(mi))])
    remove_right_top(ax_raster)

    # Draw peri-event histogram (PETH)
    ax_peth = plt.subplot(gs[10:12], sharex= ax_spect)

    # Get peth object
    pi = mi.get_peth()  # peth info
    pi.get_fr(norm_method='factor', norm_factor=row['baselineFR'])  # get firing rates

    for context, mean_fr in pi.mean_fr.items():
        if context == 'U':
            ax_peth.plot(pi.time_bin, mean_fr, 'b')
        elif context == 'D':
            ax_peth.plot(pi.time_bin, mean_fr, 'm')

    ax_peth.set_ylabel('Norm. FR', fontsize=font_size)
    # fr_ymax = myround(ax_peth.get_ylim()[1], base=10)
    # ax_peth.set_ylim(0, fr_ymax)
    # plt.yticks([0, ax_peth.get_ylim()[1]], [str(0), str(int(fr_ymax))])

    # Mark the baseline firing rat    es
    # ax_raster.axhline(y=motif_ind - 1, color='k', ls='-', lw=0.5)

    # pi.fr_smoothed = gaussian_filter1d(pi.fr, gauss_std)
    # ax_peth.plot(pi.time_bin, np.mean(pi.fr_smoothed, axis=0), 'k')
    remove_right_top(ax_peth)


    plt.show()