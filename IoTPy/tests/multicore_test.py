"""
This module contains tests:
* test_single_process_single_source()
* test_single_process_multiple_sources()
* offset_estimation_test()
which tests code from multicore.py in multiprocessing.

"""

import sys
import os
sys.path.append(os.path.abspath("../multiprocessing"))
sys.path.append(os.path.abspath("../core"))
sys.path.append(os.path.abspath("../agent_types"))
sys.path.append(os.path.abspath("../../examples/timing"))

from multicore import StreamProcess, single_process_single_source
from multicore import single_process_multiple_sources
from multicore import make_process, run_multiprocess
#from multicore import process_in_multicore
from stream import Stream
from merge import zip_stream, blend
from source import source_function
from op import map_element, map_window
from timing import offsets_from_ntp_server, print_stream


def test_single_process_single_source():
    """
    The single source generates 1, 2, 3, 4, .....
    The compute function multiplies this sequence by 10
    and puts the result in the file called test.dat
    num_steps is the number of values output by the source.
    For example, if num_steps is 4 and test.dat is empty before the
    function is called then, test.dat will contain 10, 20, 30, 40
    on separate lines.

    The steps for creating the process are:
    (1) Define the source: source()
    (2) Define the computational network: compute()
    (3) Call single_process_single_source()

    """

    def source(s):
        # A simple source which outputs 1, 2, 3,... on
        # stream s.
        def generate_sequence(state): return state+1, state+1

        # Return a thread object which takes 10 steps, and
        # sleeps for 0.1 seconds between successive steps, and
        # puts the next element of the sequence in stream s,
        # and starts the sequence with value 0.
        return source_function(
            func=generate_sequence, out_stream=s,
            time_interval=0.1, num_steps=4, state=0)

    def compute(s):
        # A trivial example of a network of agents consisting
        # of two agents where the network has a single input
        # stream: s.
        # The first agent applies function f to each element 
        # of the input stream, s, and puts the result in its
        # output stream t.
        # The second agent puts values in its input stream t
        # on a file called test.dat.
        from op import map_element
        from sink import stream_to_file

        def f(x): return x*10
        t = Stream()
        map_element(
            func=f, in_stream=s, out_stream=t)
        stream_to_file(in_stream=t, filename='test.dat')

    # Create a process with two threads: a source thread and
    # a compute thread. The source thread executes the function
    # g, and the compute thread executes function h.
    single_process_single_source(
        source_func=source, compute_func=compute)


def test_single_process_multiple_sources():
    """
    This example has two sources: source_0 generates 1, 2, 3, 4, ...
    and source_1 generates random numbers. The computation zips the two
    streams together and writes the result to a file called
    output.dat.
    
    num_steps is the number of values produced by the source. For
    example, if the smaller of the num_steps for each source is 10,
    then (1, r1), (2, r2), ..., (10, r10), ... will be appended to the
    file  output.dat where r1,..., r10 are random numbers.
 
    The steps for creating the process are:
    (1) Define the source: source()
    (2) Define the computational network: compute()
    (3) Call single_process_multiple_sources()

    """
    import random

    def source_0(s):
        # A simple source which outputs 1, 2, 3, 4, .... on
        # stream s.
        def generate_sequence(state):
            return state+1, state+1

        # Return a thread object which takes 10 steps, and
        # sleeps for 0.1 seconds between successive steps, and
        # puts the next element of the sequence in stream s,
        # and starts the sequence with value 0.
        
        return source_function(
            func=generate_sequence, out_stream=s,
            time_interval=0.1, num_steps=10, state=0)

    def source_1(s):
        # A simple source which outputs random numbers
        # stream s.

        # Return a thread object which takes 12 steps, and
        # sleeps for 0.05 seconds between successive steps, and
        # puts the next element of the sequence in stream s.
        return source_function(
            func=random.random, out_stream=s,
            time_interval=0.05, num_steps=12)

    def compute(list_of_two_streams):
        # A trivial example of a network of agents consisting
        # of two agents where the network has a single input
        # stream: s.
        # The first agent zips the two input streams and puts
        # the result on stream t.
        # The second agent puts values in its input stream t
         # on a file called output.dat.
        from sink import stream_to_file
        t = Stream()
        zip_stream(in_streams=list_of_two_streams, out_stream=t)
        stream_to_file(in_stream=t, filename='output.dat')

    # Create a process with three threads: two source threads and
    # a compute thread. The source threads execute the functions
    # source_0 and source_1, and the compute thread executes function
    # compute. 
    single_process_multiple_sources(
        list_source_func=[source_0, source_1], compute_func=h)
    

def offset_estimation_test():
    """
    Another test of single_process_multiple_sources().
    This process has two sources, each of which receives ntp offsets
    from ntp servers. The computational network consists of:
    (1) an agent that merges the two sources, and
    (2) an agent that computes the average of the merged stream over a
    window, and
    (3) a sink agent that prints the averaged stream.

    The steps for creating the process are:
    (1) Define the source: source()
    (2) Define the computational network: compute()
    (3) Call single_process_multiple_sources()

    """
    ntp_server_0 = '0.us.pool.ntp.org'
    ntp_server_1 = '1.us.pool.ntp.org'
    time_interval = 0.1
    num_steps = 20
    def average_of_list(a_list):
        if a_list:
            # Remove None elements from the list
            a_list = [i for i in a_list if i is not None]
            return sum(a_list)/float(len(a_list))
        else:
            return 0.0

    def source_0(out_stream):
        return offsets_from_ntp_server(
            out_stream, ntp_server_0, time_interval, num_steps)

    def source_1(out_stream):
        return offsets_from_ntp_server(
            out_stream, ntp_server_1, time_interval, num_steps)

    def compute(in_streams):
        merged_stream = Stream('merge in_streams')
        averaged_stream = Stream('average merged stream')
        # Create agent that merges streams
        blend(
            func=lambda x: x, in_streams=in_streams,
            out_stream=merged_stream)
        # Create agent that computes average over time window of
        # merged streams. 
        map_window(
            func=average_of_list,
            in_stream=merged_stream,out_stream=averaged_stream,
            window_size=2, step_size=1)
        # Create sink agent that prints the averaged stream.
        print_stream(averaged_stream)

    # Make the process
    single_process_multiple_sources(
        list_source_func=[source_0, source_1],
        compute_func=compute)
        
    

def test_multicore_two_processes():
    def ff(x):
        return x*10
    def gg(state):
        return state+1, state+1
    def h(v):
        print 'h is', 2*v
        return 200*v
    def source(out_stream):
        return source_function(
            func=gg, out_stream=out_stream,
            time_interval=0.1, num_steps=10, state=0, window_size=1,
            name='source')
    def compute_0(in_streams, out_streams):
        map_element(
            func=ff, in_stream=in_streams[0],
            out_stream=out_streams[0], name='aaaa')
    def compute_1(in_streams, out_streams):
        map_element(
            func=h, in_stream=in_streams[0],
            out_stream=out_streams[0], name='aaaa')
    proc_0 = make_process(
        list_source_func=[source], compute_func=compute_0,
        #process_name='proc_0',
        in_stream_names=[], out_stream_names=['t'])
    proc_1 = make_process(
        list_source_func=[], compute_func=compute_1,
        #process_name='proc_1',
        in_stream_names=['t'], out_stream_names=['u'],
        )
    run_multiprocess(
        processes=[proc_0, proc_1],
        connections=[(proc_0, 't', proc_1, 't')])

if __name__ == '__main__':
    ## test_single_process_multiple_sources()
    test_single_process_single_source()
    ## test_multicore_two_processes()
    ## offset_estimation_test()
