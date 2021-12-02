"""
Get time-shifted cross-correlation between song and firing rates
Only for Undir
"""

from analysis.parameters import peth_parm, freq_range, peth_parm, tick_length, tick_width, note_color, nb_note_crit
from analysis.spike import MotifInfo, AudioData
from database.load import DBInfo, ProjectLoader, create_db
import matplotlib.colors as colors
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from util import save
import seaborn as sns
from util.functions import myround
from util.draw import remove_right_top
import warnings

warnings.filterwarnings('ignore')


def get_binary_song(onsets, offsets):
    """
    Get binarized song signal (0 for silence, 1 for song)
    Parameters
    ----------
    onsets : arr
        syllable onsets
    offsets : arr
        syllable offsets
    Returns
    -------
    song_ts : arr
        song timestamp
    binary_song : arr
        binarized song signal
    """
    from math import ceil
    motif_duration = offsets[-1] - onsets[0]
    song_ts = np.arange(-peth_parm['buffer'], ceil(motif_duration) + peth_parm['bin_size'], peth_parm['bin_size'])
    binary_song = np.zeros(len(song_ts))

    # binary_song[np.where(peth_parm['time_bin'] <= mi.durations[0])]
    for onset, offset in zip(onsets, offsets):
        binary_song[np.where((song_ts >= onset) & (song_ts <= offset))] = 1

    return song_ts, binary_song


def get_cross_corr(sig1, sig2, lag_lim=None):
    """Get cross-correlation between two signals"""
    from scipy import signal
    corr = signal.correlate(sig1, sig2)
    corr /= np.max(corr)
    lags = signal.correlation_lags(len(sig1), len(sig2))
    corr = corr[np.where((lags >= -lag_lim) & (lags < lag_lim))]
    lags = lags[np.where((lags >= -lag_lim) & (lags < lag_lim))]
    return corr, lags


def get_cross_corr_heatmap(note_onsets, note_offsets, fr_mat):
    """Get cross_correlation heatmap"""
    corr_mat = np.array([], dtype=np.float32)
    nb_motif = len(fr_mat)
    for motif_run in range(nb_motif):
        onsets = note_onsets[motif_run]
        offsets = note_offsets[motif_run]

        onsets = np.asarray(list(map(float, onsets)))
        offsets = np.asarray(list(map(float, offsets)))

        note_dur = offsets - onsets  # syllable duration
        onsets -= onsets[0]  # start from 0
        offsets = onsets + note_dur

        _, binary_song = get_binary_song(onsets, offsets)
        corr, lags = get_cross_corr(fr_mat[motif_run, :], binary_song, lag_lim=100)
        corr_mat = np.vstack([corr, corr_mat]) if corr_mat.size else corr  # place the first trial on the top

    peak_latency = lags[corr_mat.mean(axis=0).argmax()]
    max_cross_corr = corr_mat.mean(axis=0).max()
    return corr_mat, lags, peak_latency, max_cross_corr


# Parameters
update = False
motif_nb = 0
gaussian_std = 1
update_db = False

# Create a new db to store results
if update_db:
    db = create_db('create_song_fr_cross_corr.sql')

# SQL statement
# query = "SELECT * FROM cluster WHERE analysisOK = 1"
query = "SELECT * FROM cluster WHERE id = 34"

# Load database
db = ProjectLoader().load_db()
# SQL statement
db.execute(query)

# parameters
rec_yloc = 0.05
rec_height = 1  # syllable duration rect
text_yloc = 0.5  # text height
font_size = 10
marker_size = 0.4  # for spike count


# Loop through db
for row in db.cur.fetchall():
    # Load cluster info from db
    cluster_db = DBInfo(row)
    name, path = cluster_db.load_cluster_db()
    unit_nb = int(cluster_db.unit[-2:])
    channel_nb = int(cluster_db.channel[-2:])
    format = cluster_db.format
    motif = cluster_db.motif

    # Load class object
    mi = MotifInfo(path, channel_nb, unit_nb, motif, format, name, update=update)  # cluster object
    audio = AudioData(path, update=update)  # audio object

    # Plot spectrogram & peri-event histogram (Just the first rendition)
    # for onset, offset in zip(mi.onsets, mi.offsets):
    onsets = mi.onsets[motif_nb]
    offsets = mi.offsets[motif_nb]

    # Convert from string to array of floats
    onsets = np.asarray(list(map(float, onsets)))
    offsets = np.asarray(list(map(float, offsets)))

    # Motif start and end
    start = onsets[0] - peth_parm['buffer']
    end = offsets[-1] + peth_parm['buffer']
    duration = offsets[-1] - onsets[0]

    # Get spectrogram
    timestamp, data = audio.extract([start, end])
    spect_time, spect, spect_freq = audio.spectrogram(timestamp, data)

    # Plot figure
    fig = plt.figure(figsize=(8, 11))

    fig.set_tight_layout(False)
    fig_name = mi.name
    plt.suptitle(fig_name, y=.93)
    gs = gridspec.GridSpec(20, 8)
    gs.update(wspace=0.025, hspace=0.05)

    # Plot spectrogram
    ax_spect = plt.subplot(gs[1:3, 0:6])
    spect_time = spect_time - spect_time[0] - peth_parm['buffer']  # starts from zero
    ax_spect.pcolormesh(spect_time, spect_freq, spect,
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
    plt.setp(ax_spect.get_xticklabels(), visible=False)

    # Plot syllable duration
    ax_syl = plt.subplot(gs[0, 0:6], sharex=ax_spect)
    note_dur = offsets - onsets  # syllable duration
    onsets -= onsets[0]  # start from 0
    offsets = onsets + note_dur

    # Mark syllables
    for i, syl in enumerate(mi.motif):
        rectangle = plt.Rectangle((onsets[i], rec_yloc), note_dur[i], 0.2,
                                  linewidth=1, alpha=0.5, edgecolor='k', facecolor=note_color['Motif'][i])
        ax_syl.add_patch(rectangle)
        ax_syl.text((onsets[i] + (offsets[i] - onsets[i]) / 2), text_yloc, syl, size=font_size)
    ax_syl.axis('off')

    # Plot song amplitude
    ax_amp = plt.subplot(gs[4:6, 0:6], sharex=ax_spect)
    timestamp = timestamp - timestamp[0] - peth_parm['buffer']
    data = stats.zscore(data)
    ax_amp.plot(timestamp, data, 'k', lw=0.1)
    ax_amp.set_ylabel('Amplitude (zscore)', fontsize=font_size)
    ax_amp.set_ylim(-5, 5)
    plt.setp(ax_amp.get_xticklabels(), visible=False)
    ax_amp.set_title(f"Motif = {motif_nb}", fontsize=font_size)
    remove_right_top(ax_amp)

    # Plot binarized song & firing rates
    pi = mi.get_peth()  # peth object
    pi.get_fr(gaussian_std=gaussian_std)  # get firing rates

    # Binarized song signal (0 = silence, 1 = song) Example from the first trial
    song_ts, binary_song = get_binary_song(onsets, offsets)

    ax_song = plt.subplot(gs[7:9, 0:6], sharex=ax_spect)
    ax_song.plot(song_ts, binary_song, color=[0.5, 0.5, 0.5], linewidth=1, ls='--')
    ax_song.set_ylim([0, 1])
    ax_song.set_yticks([])
    ax_song.set_xlabel('Time (ms)', fontsize=font_size)
    ax_song.spines['left'].set_visible(False)
    ax_song.spines['top'].set_visible(False)

    # Plot firing rates on the same axis
    ax_fr = ax_song.twinx()
    ax_fr.plot(pi.time_bin, pi.fr['U'][motif_nb, :], 'k')
    ax_fr.set_ylabel('FR (Hz)', fontsize=font_size)
    fr_ymax = myround(round(ax_fr.get_ylim()[1], 3), base=5)
    ax_fr.set_ylim(0, fr_ymax)
    plt.yticks([0, ax_fr.get_ylim()[1]], [str(0), str(int(fr_ymax))])
    ax_fr.spines['left'].set_visible(False)
    ax_fr.spines['top'].set_visible(False)

    # Plot cross-correlation between binarized song and firing rates
    ax_corr = plt.subplot(gs[10:12, 1:5])
    corr, lags = get_cross_corr(pi.fr['U'][motif_nb, :], binary_song, lag_lim=100)
    ax_corr.plot(lags, corr, 'k')
    ax_corr.set_ylabel('Cross-correlation', fontsize=font_size)
    ax_corr.set_xlabel('Time (ms)', fontsize=font_size)
    ax_corr.set_xlim([-100, 100])
    ax_corr.axvline(x=lags[corr.argmax()], color='r', linewidth=1, ls='--')  # mark the peak location
    remove_right_top(ax_corr)
    del corr, lags

    # Get cross-correlation heatmap across all renditions
    corr_mat, lags, peak_latency, max_cross_corr = get_cross_corr_heatmap(mi.onsets, mi.offsets, pi.fr['U'])

    ax_heatmap = plt.subplot(gs[14:16, 1:5])
    sns.heatmap(corr_mat,
                vmin=0.5, vmax=1,
                cmap='binary',
                cbar=False,
                ax=ax_heatmap
                )
    ax_heatmap.set_ylabel('Renditions')
    ax_heatmap.set_title('All renditions')
    ax_heatmap.set_yticks([])
    ax_heatmap.set_xticks([])
    remove_right_top(ax_heatmap)

    # Get the cross-corr mean across all renditions
    ax_corr_mean = plt.subplot(gs[17:19, 1:5])
    ax_corr_mean.plot(lags, corr_mat.mean(axis=0), 'k')
    ax_corr_mean.set_ylabel('Cross-correlation', fontsize=font_size)
    ax_corr_mean.set_xlabel('Time (ms)', fontsize=font_size)
    ax_corr_mean.set_xlim([-100, 100])
    ax_corr_mean.axvline(x=peak_latency, color='r', linewidth=1, ls='--')  # mark the peak location
    remove_right_top(ax_corr_mean)

    # Print out results on the figure
    txt_xloc = -0.5
    txt_yloc = 1
    txt_inc = 1  # y-distance between texts within the same section

    ax_txt = plt.subplot(gs[14, 6])
    ax_txt.set_axis_off()  # remove all axes
    ax_txt.text(txt_xloc, txt_yloc,
                f"# Motifs (Undir) = {len(pi.fr['U'])}",
                fontsize=font_size)
    txt_yloc -= txt_inc

    ax_txt.text(txt_xloc, txt_yloc,
                f"Gauss std = {gaussian_std}",
                fontsize=font_size)
    txt_yloc -= txt_inc

    ax_txt.text(txt_xloc, txt_yloc,
                f"Cross-corr max = {max_cross_corr : 0.3f}",
                fontsize=font_size)
    txt_yloc -= txt_inc

    ax_txt.text(txt_xloc, txt_yloc,
                f"Peak latency = {peak_latency} (ms)",
                fontsize=font_size)
    txt_yloc -= txt_inc

    plt.show()
