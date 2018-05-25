import datetime
import time
import random

class EventgenTimestamp(object):

    @staticmethod
    def get_random_timestamp(earliest, latest, sample_earliest, sample_latest):
        '''

        earliest and latest timestamp gets generated with an interval
        sample_earliest and sample_latest are the user config key values from eventgen.conf
        we are using earliest as a pivot time and creating a random variance using sample_earliest and sample_latest.
        in this way, we respect an interval passed in by a user and use user input earliest and latest to create a random variance
        '''
        if type(earliest) != datetime.datetime or type(latest) != datetime.datetime:
            raise Exception("Earliest {0} or latest {1} arguments are not datetime objects".format(earliest, latest))
        earliest_in_epoch = time.mktime(earliest.timetuple())
        latest_in_epoch = time.mktime(latest.timetuple())
        if earliest_in_epoch > latest_in_epoch:
            raise Exception("Latest time is earlier than earliest time.")
        pivot_time = earliest_in_epoch
        sample_earliest_in_seconds = EventgenTimestamp._convert_time_difference_to_seconds(sample_earliest)
        sample_latest_in_seconds = EventgenTimestamp._convert_time_difference_to_seconds(sample_latest)
        earliest_pivot_time = pivot_time + sample_earliest_in_seconds
        latest_pivot_time = pivot_time + sample_latest_in_seconds
        pivot_time_range = latest_pivot_time - earliest_pivot_time
        random_pivot_time = earliest_pivot_time + random.randint(0, pivot_time_range)
        return datetime.datetime.fromtimestamp(random_pivot_time)


    @staticmethod
    def _convert_time_difference_to_seconds(time_difference):
        '''

        :param time_difference: can be "now" or <int>ms, <int>s, <int>m, <int>h, <int>d with + or - prefix
        :return: seconds in difference
        '''
        if time_difference == "now":
            return 0.0
        else:
            if time_difference[-2:] == 'ms':
                time_value_in_seconds = float(time_difference[1:-2]) * 0.001
            elif time_difference[-1] == 's':
                time_value_in_seconds = float(time_difference[1:-1])
            elif time_difference[-1] == 'm':
                time_value_in_seconds = float(time_difference[1:-1]) * 60
            elif time_difference[-1] == 'h':
                time_value_in_seconds = float(time_difference[1:-1]) * 60 * 60
            elif time_difference[-1] == 'd':
                time_value_in_seconds = float(time_difference[1:-1]) * 60 * 60 * 24
            else:
                time_value_in_seconds = 0.0

            if time_difference[0] == "-":
                negative_time_value_in_seconds = time_value_in_seconds * -1
                return negative_time_value_in_seconds
            else:
                return time_value_in_seconds
