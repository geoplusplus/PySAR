#! /usr/bin/env python
############################################################
# Program is part of PySAR v1.0                            #
# Copyright(c) 2013, Heresh Fattahi                        #
# Author:  Heresh Fattahi                                  #
############################################################
# Yunjun, Dec 2015: Add support for coherence/wrapped, update display
# Yunjun, Jun 2016: Add plot_network(), plot_bperp_hist(),
#                   axis_adjust_date_length(), igram_pairs()


import sys
import os
import argparse

import numpy as np
import matplotlib.pyplot as plt

import pysar._pysar_utilities as ut
import pysar._datetime as ptime
import pysar._network  as pnet
import pysar._readfile as readfile
from pysar._readfile import multi_group_hdf5_file, multi_dataset_hdf5_file, single_dataset_hdf5_file

  
######################################
BL_LIST='''
070106     0.0   0.03  0.0000000  0.00000000000 2155.2 /scratch/SLC/070106/
070709  2631.9   0.07  0.0000000  0.00000000000 2155.2 /scratch/SLC/070709/
070824  2787.3   0.07  0.0000000  0.00000000000 2155.2 /scratch/SLC/070824/
'''

DATE12_LIST='''
070709-100901
070709-101017
070824-071009
'''

EXAMPLE='''example:
  plot_network.py unwrapIfgram.h5
  plot_network.py unwrapIfgram.h5 --coherence coherence_spatialAverage.list --save
  plot_network.py Modified_coherence.h5 --save
  plot_network.py Modified_coherence.h5 --nodisplay
  plot_network.py Pairs.list               -b bl_list.txt
  plot_network.py unwrapIfgram_date12.list -b bl_list.txt
'''


def cmdLineParse():
    parser = argparse.ArgumentParser(description='Display Network of Interferograms',\
                                     formatter_class=argparse.RawTextHelpFormatter,\
                                     epilog=EXAMPLE)
    
    parser.add_argument('file',\
                        help='file with network information, supporting:\n'+\
                             'HDF5 file: unwrapIfgram.h5, Modified_coherence.h5\n'+\
                             'Text file: list of date12, generated by selectPairs.py or plot_network.py, i.e.:'+DATE12_LIST)
    parser.add_argument('-b','--bl','--baseline', dest='bl_list_file', default='bl_list.txt',\
                        help='baseline list file, generated using createBaselineList.pl, i.e.:'+BL_LIST)
    parser.add_argument('--coherence', dest='coherence_list_file',\
                        help='display pairs in color based on input coherence\n'+\
                             'i.e. coherence_spatialAverage.list (generated by spatial_average.py)')

    # Figure  Setting
    fig_group = parser.add_argument_group('Figure','Figure settings for display')
    fig_group.add_argument('--fontsize', type=int, default=12, help='font size in points')
    fig_group.add_argument('--lw','--linewidth', dest='linewidth', type=int, default=2, help='line width in points')
    fig_group.add_argument('--mc','--markercolor', dest='markercolor', default='orange', help='marker color')
    fig_group.add_argument('--ms','--markersize', dest='markersize', type=int, default=16, help='marker size in points')

    fig_group.add_argument('--dpi', dest='fig_dpi', type=int, default=150,\
                           help='DPI - dot per inch - for display/write')
    fig_group.add_argument('--figsize', dest='fig_size', type=float, nargs=2,\
                           help='figure size in inches - width and length')
    fig_group.add_argument('--figext', dest='fig_ext',\
                           default='.pdf', choices=['.emf','.eps','.pdf','.png','.ps','.raw','.rgba','.svg','.svgz'],\
                           help='File extension for figure output file')
    
    fig_group.add_argument('--save', dest='save_fig', action='store_true',\
                           help='save the figure')
    fig_group.add_argument('--nodisplay', dest='disp_fig', action='store_false',\
                           help='save and do not display the figure')

    inps = parser.parse_args()
    if not inps.disp_fig:
        inps.save_fig = True
    
    return inps


##########################  Main Function  ##############################
def main(argv):
    inps = cmdLineParse()
    print '\n******************** Plot Network **********************'

    # Output figure name
    figName1 = 'BperpHist'+inps.fig_ext
    figName2 = 'Network'+inps.fig_ext
    if 'Modified' in inps.file:
        figName1 = 'BperpHist_Modified'+inps.fig_ext
        figName2 = 'Network_Modified'+inps.fig_ext

    ##### 1. Read Info
    # Read dateList and bperpList
    ext = os.path.splitext(inps.file)[1]
    if ext in ['.h5']:
        k = readfile.read_attribute(inps.file)['FILE_TYPE']
        print 'reading date and perpendicular baseline from '+k+' file: '+os.path.basename(inps.file)
        if not k in multi_group_hdf5_file:
            print 'ERROR: only the following file type are supported:\n'+str(multi_group_hdf5_file)
            sys.exit(1)
        Bp = ut.Baseline_timeseries(inps.file)
        date8List = ptime.igram_date_list(inps.file)
        date6List = ptime.yymmdd(date8List)
    else:
        print 'reading date and perpendicular baseline from baseline list file: '+inps.bl_list_file
        date8List, Bp = pnet.read_baseline_file(inps.bl_list_file)[0:2]
        date6List = ptime.yymmdd(date8List)
    print 'number of acquisitions: '+str(len(date8List))

    # Read Pairs Info
    print 'reading pairs info from file: '+inps.file
    date12_list = pnet.get_date12_list(inps.file)
    pairs_idx = pnet.date12_list2index(date12_list, date6List)
    print 'number of pairs       : '+str(len(pairs_idx))

    # Read Coherence List
    inps.coherence_list = None
    if inps.coherence_list_file:
        fcoh = np.loadtxt(inps.coherence_list_file, dtype=str)
        inps.coherence_list = [float(i) for i in fcoh[:,1]]
        coh_date12_list = [i for i in fcoh[:,0]]
        if not set(coh_date12_list) == set(date12_list):
            print 'WARNING: input coherence list has different pairs/date12 from input file'
            print 'turn off the color plotting of interferograms based on coherence'
            inps.coherence_list = None
    
    ##### 2. Plot
    # Fig 1 - Baseline History
    fig1 = plt.figure(1)
    ax1 = fig1.add_subplot(111)
    ax1 = pnet.plot_perp_baseline_hist(ax1, date8List, Bp, vars(inps))

    if inps.save_fig:
        fig1.savefig(figName1,bbox_inches='tight')
        print 'save figure to '+figName1

    # Fig 2 - Interferogram Network
    fig2 = plt.figure(2)
    ax2 = fig2.add_subplot(111)
    ax2 = pnet.plot_network(ax2, pairs_idx, date8List, Bp, vars(inps), inps.coherence_list)

    if inps.save_fig:
        # Save network/date12 to text file
        txtFile = os.path.splitext(inps.file)[0]+'_date12.list'
        np.savetxt(txtFile, date12_list, fmt='%s')
        print 'save pairs/date12 info to file: '+txtFile
        # Save Network figure
        fig2.savefig(figName2,bbox_inches='tight')
        print 'save figure to '+figName2

    if inps.disp_fig:
        plt.show() 

############################################################
if __name__ == '__main__':
    main(sys.argv[1:])



