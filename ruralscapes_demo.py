import os
import sys

import fire

import segprop
import stats
import numpy as np


"""
Prerequisites:
Optical Flow extracted to PATH/flow_2k_fn2 (frame, width, height, XY vectors) in h5 databases.
NPZ labels in PATH/labels_2k (width, height, classes) true/false hard maps - Check & run ruralscapes_preprocess.py.
"""

PATH = '/home/nonari/windows/ruralscapes'

train_videos = ['0043', '0044', '0045', '0046', '0047', '0050', '0053', '0085', '0093', '0097', '0101', '0114', '0118']     # train set videos
train_videos = ['0050', '0043']       # demo video
iterations = 3
device = 'cuda'


# define function that returns true for GT frame indices (for forwarding GT frames unchanged between iterations)
def frame_copy(index):
    return np.mod(index, 100) == 0


# define function that returns true for frames without evaluation labels (filtering out non-GT frames for test purposes)
def frame_filter(index):
    return (np.mod(index, 50) != 0) or (np.mod(index, 50 * 2) == 0)


every_ten = lambda x: x % 10 != 0 or x % 25 == 0


def main(vid=None, start_from=None, stop_at=None):
    # process GT and generate intermediary labels
    if vid is not None:
        videos = [vid]
    else:
        videos = train_videos
    if iterations > 0:
        for video in videos:
            segprop.vote((os.path.join(PATH, 'flow_farneback', 'DJI_' + video + '_forward.h5'),
                          os.path.join(PATH, 'flow_farneback', 'DJI_' + video + '_backward.h5')),
                         os.path.join(PATH, 'labels', 'sparse_labels', 'DJI_' + video),
                         os.path.join(PATH, 'output_2k', 'i01', 'DJI_' + video),
                         precalc_flow=False, start_from=start_from, stop_at=stop_at, device=device, overwrite=False, frame_filter=every_ten)

    # run a few segprop iterations
    for it in range(2, iterations + 1):
        for video in videos:
            segprop.iterate((os.path.join(PATH, 'flow_farneback', 'DJI_' + video + '_forward.h5'),
                             os.path.join(PATH, 'flow_farneback', 'DJI_' + video + '_backward.h5')),
                            os.path.join(PATH, 'output_2k', 'i{:02d}'.format(it - 1), 'DJI_' + video),
                            os.path.join(PATH, 'output_2k', 'i{:02d}'.format(it), 'DJI_' + video),
                            pv_series=[0, 5, 10], frame_copy=frame_copy, device=device, overwrite=False, frame_filter=every_ten)

    # apply the final filtering step over the evaluation frames
    for video in videos:
        segprop.denoise((os.path.join(PATH, 'flow_farneback', 'DJI_' + video + '_forward.h5'),
                         os.path.join(PATH, 'flow_farneback', 'DJI_' + video + '_backward.h5')),
                        os.path.join(PATH, 'output_2k', 'i{:02d}'.format(iterations - 1), 'DJI_' + video),
                        os.path.join(PATH, 'output_2k', 'i{:02d}'.format(iterations), 'DJI_' + video + '_filtered-test_frames'),
                        pv_series=[0, 1, 3, 5, 7], method='self', frame_filter=frame_filter, device=device, overwrite=False)

    # evaluate
    fmeasure, miou = stats.evaluate(os.path.join(PATH, 'output_2k', 'i{:02d}'.format(iterations)), os.path.join(PATH, 'labels_2k', 'train_odd'))
    print('fmeasure', fmeasure)
    print('miou', miou)


if __name__ == '__main__':
    fire.Fire(main)
