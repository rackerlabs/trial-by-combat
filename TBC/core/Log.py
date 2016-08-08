import time
import sys
from network_cjl.Serializer import *
from TBC.utility.Numbers import *

@serializable({'num':int, 'failed':int, 'total_time': float, 'latency': float, 'tput': float})
class EventInfo(object):
    def __init__(self):
        self.num = 0
        self.failed = 0
        self.total_time = 0
        self.latency = None
        self.tput = None


@serializable({'events': {str: EventInfo}, 'start_time': float, 'end_time': float})
class LogFrame(object):
    """
    Represents a large number of events within a time span
    """

    def __init__(self, start_time):
        self.events = {}
        self.start_time = start_time
        self.end_time = None

    def log(self, event, delta_t, failed):
        """
        Adds the event to the frame but does not to any processing
        :param event: a list representing an event (the 'path' returned by a task report)
        :param delta_t: the amount of time it took for this event to complete
        :param failed: True if this event failed
        """

        if event not in self.events:
            self.events[event] = EventInfo()

        e_info = self.events[event]
        e_info.num += 1
        e_info.total_time += delta_t
        if failed:
            e_info.failed += 1

    def process(self, end_time):
        """
        Finish up computation on this frame
        :param delta_time: the amount of time that this frame represents
        """
        self.end_time = end_time
        delta_time = self.end_time - self.start_time
        for event in self.events:
            e_info = self.events[event]
            e_info.latency = significant_figures(e_info.total_time / float(e_info.num), 4)
            e_info.tput = significant_figures(float(e_info.num) / delta_time, 4)


@serializable({'frames': [LogFrame],
               'latency_bin_size': float,
               'latency_bins': {str: {int: int}},
               'framerate': float})
class Logger(object):
    """
    Keeps a sequence of log frames
    """

    def __init__(self, framerate, latency_bin_size):
        """
        Construct a new logger
        :param framerate: the number of frames per second to store
        """
        self.frames = []
        self.frame_number = -1

        self.latency_bin_size = latency_bin_size
        self.latency_bins = {}

        self.framerate = framerate
        self.frame_period = 1.0 / self.framerate

        # massage the start time so that it starts on an "even" interval
        self.start_time = time.time()
        self.start_time = self.start_time - (self.start_time % self.frame_period)

    def update_frame(self):
        """
        Ensure that the last frame in self.frames represents the frame for now
        """
        now = time.time()
        delta_time = now - self.start_time

        target_frame = int(delta_time / self.frame_period)

        # add frames until we reach the target frame
        while self.frame_number < target_frame:
            boundary_time = self.start_time + self.frame_number * self.frame_period
            if self.frame_number >= 0:
                self.frames[-1].process(boundary_time)
            self.frames.append(LogFrame(boundary_time))
            self.frame_number += 1

    def log_latency_percentile(self, event, latency):
        lbin = None

        if event in self.latency_bins:
            lbin = self.latency_bins[event]
        else:
            lbin = {}
            self.latency_bins[event] = lbin

        latency_bin = int(latency / self.latency_bin_size)
        if latency_bin in lbin:
            lbin[latency_bin] += 1
        else:
            lbin[latency_bin] = 1

    def log(self, event, delta_t, failed):
        event = '/'.join(event)
        self.update_frame()
        self.frames[-1].log(event, delta_t, failed)
        self.log_latency_percentile(event, delta_t)

    def finish(self):
        """
        Call this at the very end after all input is recieved
        """
        boundary_time = self.start_time + self.frame_number * self.frame_period
        if self.frame_number >= 0:
            self.frames[-1].process(boundary_time)

    def __str__(self):
        result = []
        for frame in self.frames:
            result.append('-' * 100)
            result.append('start time: ' + str(frame.start_time))
            for event in frame.events:
                e_info = frame.events[event]
                result.append('\t' + str(event) + ' total: ' + str(e_info.num) + ', failed: ' + str(e_info.failed) +
                              ', latency: ' + str(e_info.latency) + ', throughput: ' + str(e_info.tput))
        for event in self.latency_bins:
            lbin = self.latency_bins[event]
            result.append('-' * 100)
            result.append('Latency histogram for ' + str(event))
            for bin in sorted(lbin.keys()):
                result.append(str(bin * self.latency_bin_size) + ': ' + str(lbin[bin]))
        return '\n'.join(result)


def clip_logs(logs, frame_size, dead_frames):
    """
    Given a list of logs, clip parts of logs that do not overlap
    :param logs: a list of Loggers
    :param frame_size: the frame size of the Loggers
    :param dead_frames: the number of additional frames to clip from the front and the back
    :return:  a list of Loggers
    """
    max_begin = logs[0].frames[0].start_time
    min_end = logs[0].frames[-1].start_time

    for log in logs:
        begin_frame = log.frames[0]
        end_frame = log.frames[-1]
        max_begin = max(max_begin, begin_frame.start_time + dead_frames * frame_size)
        min_end = min(min_end, end_frame.start_time - dead_frames * frame_size)

    if max_begin >= min_end:
        sys.stderr.write("Invalid benchmark data: runtimes to not overlap\n")
        return None

    max_begin = ApproximateFloat(max_begin, threshold=0.1*frame_size)
    min_end = ApproximateFloat(min_end, threshold=0.1*frame_size)

    for log in logs:
        new_frames = []
        for frame in log.frames:
            if frame.start_time >= max_begin and frame.start_time <= min_end:
                new_frames.append(frame)

        log.frames = new_frames
    return logs


def average_logs(logs):
    """
    Given a list of logs (with frames that fully overlap), return a single log that is an aggregation of all logs
    :param logs: a list of Loggers
    :return: a Logger
    """
    average_log = Logger(logs[0].framerate, logs[0].latency_bin_size)

    number_of_frames = len(logs[0].frames)

    # assert that each log has the same number of frames
    for log in logs:
        assert len(log.frames) == number_of_frames, 'Frame numbers do not match!  ' \
                                                    'Expected %d frames, got %d instead.' \
                                                    % (number_of_frames, len(log.frames))

    # average the LogFrames
    # for each frame
    for frame_number in xrange(number_of_frames):
        next_frame = LogFrame(logs[0].frames[frame_number].start_time)

        # for each log
        for log in logs:
            # for each type of event in this frame
            for event in log.frames[frame_number].events:
                if event not in next_frame.events:
                    next_frame.events[event] = EventInfo()
                next_frame.events[event].num += log.frames[frame_number].events[event].num
                next_frame.events[event].failed += log.frames[frame_number].events[event].failed
                next_frame.events[event].total_time += log.frames[frame_number].events[event].total_time

        next_frame.process(logs[0].frames[frame_number].end_time)
        average_log.frames.append(next_frame)

    # sum the latency bins
    for log in logs:
        for event_type in log.latency_bins:
            if event_type not in average_log.latency_bins:
                average_log.latency_bins[event_type] = {}
            for bin in log.latency_bins[event_type]:
                if bin not in average_log.latency_bins[event_type]:
                    average_log.latency_bins[event_type][bin] = 0
                average_log.latency_bins[event_type][bin] += log.latency_bins[event_type][bin]

    return average_log


def print_log(log):
    """
    A way of visualizing a log for debugging purposes
    """
    for frame in log.frames:
        print '-' * 100
        print 'start time: ' + str(frame.start_time)
        for event in frame.events:
            e_info = frame.events[event]
            print '\t' + str(event) + ' total: ' + str(e_info.num) + ', failed: ' + str(e_info.failed) + \
                  ', latency: ' + str(e_info.latency) + ', throughput: ' + str(e_info.tput)
    for event in log.latency_bins:
        lbin = log.latency_bins[event]
        print '-' * 100
        print 'Latency histogram for ' + str(event)
        for bin in sorted(lbin.keys()):
            print str(bin * log.latency_bin_size) + ': ' + str(lbin[bin])