"""Compare spike fano factor between different conditions"""


def plot_fano_factor_cluster(save_fig=True,
                             view_folder=False,
                             fig_ext='.png'):
    import numpy as np
    from util import save

    # # SQL statement
    # Fano factor at the motif level
    df = db.to_dataframe("SELECT * FROM cluster WHERE analysisOK=TRUE")
    df.set_index('id')

    # Parameters
    nb_row = 3
    nb_col = 2

    # Plot the results
    fig, ax = plt.subplots(figsize=(6, 4))
    plt.suptitle('Fano Factor', y=.9, fontsize=20)

    # Undir
    df['fanoSpkCountUndir'].replace('', np.nan, inplace=True)  # replace empty values with nans to prevent an error
    ax = plt.subplot2grid((nb_row, nb_col), (1, 0), rowspan=2, colspan=1)
    plot_bar_comparison(ax, df['fanoSpkCountUndir'], df['taskName'], hue_var=df['birdID'],
                        title='Undir', ylabel='Fano Factor',
                        y_lim=[0, round(df['fanoSpkCountUndir'].max()) + 1],
                        col_order=("Predeafening", "Postdeafening")
                        )

    # Dir
    df['fanoSpkCountDir'].replace('', np.nan, inplace=True)  # replace empty values with nans to prevent an error
    ax = plt.subplot2grid((nb_row, nb_col), (1, 1), rowspan=2, colspan=1)
    plot_bar_comparison(ax, df['fanoSpkCountDir'], df['taskName'], hue_var=df['birdID'],
                        title='Dir',
                        y_lim=[0, round(df['fanoSpkCountDir'].max()) + 1],
                        col_order=("Predeafening", "Postdeafening")
                        )
    fig.tight_layout()

    # Save results
    if save_fig:
        save_path = save.make_dir(ProjectLoader().path / 'Analysis', 'Results')
        save.save_fig(fig, save_path, 'FanoFactor', fig_ext=fig_ext, view_folder=view_folder)
    else:
        plt.show()


def plot_fano_factor_syllable(save_fig=True,
                              view_folder=False,
                              fig_ext='.png'):

    from util import save

    # Parameters
    nb_row = 3
    nb_col = 2

    # Fano factor (spike counts)
    fig, ax = plt.subplots(figsize=(7, 4))
    plt.suptitle(f"Fano Factor (FR >= {fr_crit} # of Notes >= {nb_note_crit})", y=.9, fontsize=20)

    # Undir
    query = f"SELECT * FROM syllable_pcc WHERE nbNoteUndir >= {nb_note_crit} AND frUndir >= {fr_crit}"
    df = db.to_dataframe(query)
    ax = plt.subplot2grid((nb_row, nb_col), (1, 0), rowspan=2, colspan=1)
    plot_bar_comparison(ax, df['fanoFactorUndir'], df['taskName'],
                        hue_var=df['birdID'],
                        title='Undir', ylabel='Fano factor',
                        y_lim=[0, 6],
                        col_order=("Predeafening", "Postdeafening"),
                        )

    # Dir
    query = f"SELECT * FROM syllable_pcc WHERE nbNoteDir >= {nb_note_crit} AND frDir >= {fr_crit}"
    df = db.to_dataframe(query)
    ax = plt.subplot2grid((nb_row, nb_col), (1, 1), rowspan=2, colspan=1)
    plot_bar_comparison(ax, df['fanoFactorDir'], df['taskName'],
                        hue_var=df['birdID'],
                        title='Dir',
                        y_lim=[0, round(df['fanoFactorDir'].max() * 10) / 10 + 0.2],
                        col_order=("Predeafening", "Postdeafening"),
                        legend_ok=True
                        )
    fig.tight_layout()

    # Save results
    if save_fig:
        save_path = save.make_dir(ProjectLoader().path / 'Analysis', 'Results')
        save.save_fig(fig, save_path, 'FanoFactor', fig_ext=fig_ext, view_folder=view_folder)
    else:
        plt.show()


if __name__ == '__main__':

    from database.load import ProjectLoader
    from deafening.plot import plot_paired_scatter
    from results.plot import plot_bar_comparison
    import matplotlib.pyplot as plt

    save_fig = False
    view_folder = True  # open the folder where the result figures are saved
    fig_ext = '.png'

    nb_note_crit = 10
    fr_crit = 10

    # Load database
    db = ProjectLoader().load_db()

    # plot_fano_factor_cluster(
    #     save_fig=save_fig,
    #     view_folder=view_folder,
    #     fig_ext=fig_ext
    # )

    # plot_fano_factor_syllable(
    #     save_fig=save_fig,
    #     view_folder=view_folder,
    #     fig_ext=fig_ext
    # )

    # Load database
    query = f"SELECT * FROM syllable_pcc WHERE nbNoteUndir >= {nb_note_crit} AND " \
            f"nbNoteDir >= {nb_note_crit} AND " \
            f"frUndir >= {fr_crit} AND " \
            f"frDir >= {fr_crit}"

    df = db.to_dataframe(query)

    plot_paired_scatter(df, 'fanoFactorDir', 'fanoFactorUndir',
                        save_folder_name='FanoFactor',
                        x_lim=[0, 4],
                        y_lim=[0, 4],
                        x_label='Dir',
                        y_label='Undir',
                        title=f"Fano Factor (FR >= {fr_crit} # of Notes >= {nb_note_crit}) (Paired)",
                        save_fig=False,
                        view_folder=False,
                        fig_ext='.png')


