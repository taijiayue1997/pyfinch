"""
By Jaerong
Get correlation between the number of spikes (or firing rates) and song features
"""

import matplotlib.colors as colors
import matplotlib.gridspec as gridspec

from analysis.parameters import peth_parm, freq_range, note_color, tick_width, tick_length
from analysis.spike import *
from database.load import DBInfo, ProjectLoader
from util import save
from util.draw import *
from util.spect import *
import pandas as pd


def get_pre_motor_spk_per_note(ClusterInfo, npy_update=False):
    """
    Get the number of spikes in the pre-motor window for individual note

    Parameters
    ----------
    ClusterInfo : class

    Returns
    -------
    pre_motor_spk_dict : dict
    """
    # Get number of spikes from pre-motor window per note

    from database.load import ProjectLoader
    import numpy as np

    save_path = save.make_dir(ProjectLoader().path / 'Analysis', 'PSD_similarity' + '/' + 'SpkCount',
                              add_date=False)
    npy_name = ClusterInfo.name + '.npy'
    npy_name = save_path / npy_name

    if npy_name.exists() and not npy_update:
        pre_motor_spk_dict = np.load(npy_name,
                                     allow_pickle=True).item()  # all pre-deafening data to be combined for being used as a template
    else:
        nb_pre_motor_spk = np.array([], dtype=np.int)
        note_onset_ts = np.array([], dtype=np.float32)
        all_notes = ''

        for onsets, notes, spks in zip(ClusterInfo.onsets, ClusterInfo.syllables,
                                       ClusterInfo.spk_ts):  # loop through renditions
            onsets = np.delete(onsets, np.where(onsets == '*'))
            onsets = np.asarray(list(map(float, onsets)))
            notes = notes.replace('*', '')
            for onset, note in zip(onsets, notes):  # loop through notes
                if note in motif:
                    pre_motor_win = [onset - 50, onset]
                    nb_spk = len(spks[np.where((spks >= pre_motor_win[0]) & (spks <= pre_motor_win[-1]))])
                    nb_pre_motor_spk = np.append(nb_pre_motor_spk, nb_spk)
                    note_onset_ts = np.append(note_onset_ts, onset)
                    all_notes += note

        # Store info in a dictionary
        pre_motor_spk_dict = {}
        pre_motor_spk_dict['pre_motor_win'] = 50  # pre-motor window before syllable onset in ms

        for note in unique(all_notes):
            ind = find_str(all_notes, note)
            pre_motor_spk_dict[note] = {}  # nested dictionary
            pre_motor_spk_dict[note]['nb_spk'] = nb_pre_motor_spk[ind]
            pre_motor_spk_dict[note]['onset_ts'] = note_onset_ts[ind]

        save_path = save.make_dir(ProjectLoader().path / 'Analysis', 'PSD_similarity' + '/' + 'SpkCount',
                                  add_date=False)
        npy_name = ClusterInfo.name + '.npy'
        npy_name = save_path / npy_name
        np.save(npy_name, pre_motor_spk_dict)
    return pre_motor_spk_dict


# parameters
rec_yloc = 0.05
rec_height = 1  # syllable duration rect
text_yloc = 0.5  # text height
font_size = 10
marker_size = 0.4  # for spike count
nb_note_crit = 10  # minimum number of notes for analysis

norm_method = None
fig_ext = '.png'  # .png or .pdf
update = False  # Set True for recreating a cache file
save_fig = True
update_db = False  # save results to DB
time_warp = True  # spike time warping
npy_update = True

# Create a new database (syllable)
db = ProjectLoader().load_db()
with open('database/create_motif_syllable.sql', 'r') as sql_file:
    db.conn.executescript(sql_file.read())

# Load database
query = "SELECT * FROM cluster WHERE id = 96"
db.execute(query)

# Store results in the dataframe
df = pd.DataFrame()

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
    ci = ClusterInfo(path, channel_nb, unit_nb, format, name, update=update)  # cluster object

    # Load number of spikes
    pre_motor_spk_dict = get_pre_motor_spk_per_note(ci, npy_update=npy_update)

    db.cur.execute('''INSERT OR IGNORE INTO motif_syllable (clusterID) VALUES (?)''', (row["id"],))
    db.conn.commit()
print('Done!')
