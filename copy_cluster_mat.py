"""
By Jaerong (06/29/2020)
This program copy/pastes SpkInfo.mat from each cell root to the destinatoin folder (InformationAnalysis)
"""
import os
from summary.read_config import parser
from summary import load
from summary import save

project_path = load.project(parser)  # find the project folder
summary_cluster, nb_cluster = load.summary(parser)  # load cluster summary file
del parser

# Make a folder to save files
save_path = 'InformationAnalysis'
save.make_save_dir(save_path)


save_path = os.path.join(project_path, r'Analysis\InformationAnalysis')  # the data folder where SAP feature values are stored
if not os.path.exists(save_path):
    os.mkdir(save_path)


def copy_cluster_mat(summary_cluster):

    import shutil

    for cluster_run in range(0, nb_cluster):
        cluster = load.cluster(summary_cluster, cluster_run)

        if int(cluster.AnalysisOK):
            # print(cluster)
            session_id, cell_id, cell_root = load.cluster_info(cluster)
            # print('Accessing... ' + cell_root)
            os.chdir(cell_root)

            mat_file = [file for file in os.listdir(cell_root) if file.endswith('SpkInfo.mat')][0]
            # print(mat_file)

            # Make a new folder for individual neurons
            new_save_path = os.path.join(save_path, cell_id)
            print(new_save_path)
            if not os.path.exists(new_save_path):
                os.mkdir(new_save_path)

            shutil.copy(mat_file, new_save_path)


if __name__ == '__main__':
    copy_cluster_mat(summary_cluster)
