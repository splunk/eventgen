(This Document assumes you are already familiar with [Eventgen's Architecture](Architecture.md).  It is critical you read this document first.)

# Intro

Eventgen v4 has been designed to scale, despite no small number of obstacles put in our way by Python.  Eventgen's original goals were primarily around making it simple for people to quickly build event generators for many different use cases without needing to resort to hand writing them every time.  This brings consistency and makes it simpler for others to come behind and support the work of others.  However, none of the earlier iterations really gave much thought to performance.

Prior to v4, Eventgen scaling was available only by increasing the number of samples Eventgen was running.  Each Sample was its own thread, and you could, up to a point, gain some additional scalability by adding more samples.  However, this approach quickly leads us to the first scalability blocker for Eventgen: its written in Python.

# Scaling, despite Python

I'm sure had either David or I considered that we'd eventually want to scale this thing, writing it in Python wouldn't have been the first choice.  Lets face it, Python is slow, and there's plenty of emperical evidence a quick Google away.   However, Python affords us a lot of advantages in developer productivity, and it is possible to write a minimal amount of code in other environments (C/Java/etc), write the majority in Python, and get good performance.  There's a few things we must design around, which we'll explain in detail and will lead us to a quick walkthrough of some configuration tunables we've built into Eventgen.

## The Global Interpreter Lock

The first obstacle to scaling a Python application is the Global Interpreter Lock.  Lots of information online, but long story short, only one Thread running Python code can be executed simultaneously.  Python functions written in C can run in different threads.  Threads in Python are lightweight, similar to OS threads, but they will only gain concurrency in the event that your Python program is primarily I/O bound or is spending a good portion of its time executing C-written python functions.

In the case of Eventgen, we do a non-insignificant amount of I/O, so our first step to scaling is to utilizing threading.  In Eventgen, we create a thread for each sample.  The sample acts as the master timer for that sample.  In the case of a queuable generator plugin, it will place an entry in the generator queue for generator workers to pick up.  With a non-queueable plugin, it will call the generator's `gen()` function directly.

## Growing beyond a single process

The GIL will limit our execution capacity eventually.  The next scaling capability Python affords us is the multiprocessing library.  Multiprocessing provides an API-compatible implementation of threading utilizing multiple processes instead of multiple threads to get around the GIL.  Because processes do not share memory, there are of course some limitations, but given our use case, multiprocessing works pretty well.  

We give the end user the choice between threading and processing via a tuneable in default/eventgen.conf under the [global] stanza:

    [global]
    threading = thread | process

For multiprocessing, set threading = process or pass `--multiprocess` on the command line.  This will cause eventgen to spin up a process for each generator worker and each output worker instead of a thread.  Samples will remain threads in the master process since they aren't really doing any work other than scheduling.

## Scaling up concurrency

By default, Eventgen will run one generator thread and one output thread.  This is totally fine for nearly all use cases which are not trying to generate large volumes of data.  For those wanting to scale up, we provide two tunables which allow you to scale generation and outputting independently, also in default/eventgen.conf:

    [global]
    generatorWorkers = 1
    outputWorkers = 1

Spawning multiple generators is configurable also by passing `--generators` on the comamnd line.

By default we're setup to output as a Splunk modular input, which is very fast writing to stdout.  If you're outputting to stdout, even maxing out CPU, we often only need one output worker.  If you're outputting to something which is over the network or has a higher latency, you may want to increase output workers to allow for more concurrency.

# Real-world tuning

Eventgen outputs some useful log information, by default in $SPLUNK_HOME/var/log/splunk/eventgen.log, which will tell you a bit about its performance and where we might be backlogged:

    2014-02-02 20:57:03,091 INFO Output Queue depth: 0  Generator Queue depth: 28412 Generators Per Sec: 43 Outputters Per Sec: 43
    2014-02-02 20:57:03,091 INFO Events/Sec: 87643.8 Kilobytes/Sec: 30587.330859 GB/Day: 2520.318400

Lets look at both lines.  First, we're giving you visibility into Queue depths.  Queue depths are whole numbers of worker items which are to be consumed, not total lines.  So if you have an Output Queue depth of 5, that's five whole generators work to be output, not 5 lines.  Its relatively low cost to scale up output workers, so you should always have a high enough number such that Output Queue depth stays at 0.  Generator Queue depth should also always be zero unless you're during backfill, otherwise you are falling behind and will likely never catch up.  If you're backing up, considering moving to process based threading (may be difficult as a Splunk app depending on which platform you're using).

The second line is simply a view into the performance of the app as a whole.  This helps us tune and compare apples to apples.

# Theoretical maximums

To test out our performance, we wanted to push the system to its limits.  For this, we built the windbag generator.  It does nothing but just stuff raw text into the output queue.  All the following tests and results are done on a Macbook Air which has two cores.  First, lets test the windbag plugin, with settings of 2 generator, 1 outputter, in threading mode:

    csharp-mbp15:eventgen csharp$ python bin/eventgen.py tests/perf/eventgen.conf.perfwindbag
    2014-02-02 21:18:59,606 INFO Output Queue depth: 100  Generator Queue depth: 6201 Generators Per Sec: 9 Outputters Per Sec: 9
    2014-02-02 21:18:59,666 INFO Events/Sec: 490000.0 Kilobytes/Sec: 21533.203125 GB/Day: 1774.281263

Windbag is entirely optimized for events per second.  With longer events, we could certainly up the total bytes/sec throughput.  Now, lets see if we can get better performance by seperating generating and outputting to their own process.  Running the same again, setting ``threading = process`` in ``[global]``, we get:

    csharp-mbp15:eventgen csharp$ python bin/eventgen.py tests/perf/eventgen.conf.perfwindbag
    2014-02-02 21:19:53,254 INFO Output Queue depth: 100  Generator Queue depth: 8491 Generators Per Sec: 8 Outputters Per Sec: 5
    2014-02-02 21:19:53,255 INFO Events/Sec: 270000.0 Kilobytes/Sec: 11865.234375 GB/Day: 977.665186

That's unusual.  Multiprocessing is actually way way slower!  We should dig into why this is.  If you want to know the details of how your Python program is running, the Python gods have thankfully blessed us with cProfile.  Usually, you can simply call ``python -m cProfile``, but our code is multithreaded, which doesn't work this way.  To get around this, we've provided a tunable in default/eventgen.conf:

    [global]
    profiler = true | false

Lets set this to true and run again.  Now we need to get information on the output of Python's cProfile module.  To do that:

    csharp-mbp15:eventgen csharp$ python -m pstats
    Welcome to the profile statistics browser.
    % read eventgen_outputworker_0
    eventgen_outputworker_0% sort time
    eventgen_outputworker_0% stats 5
    Sun Feb  2 21:20:00 2014    eventgen_outputworker_0

             13203031 function calls in 17.008 seconds

       Ordered by: internal time
       List reduced from 76 to 5 due to restriction <5>

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
           89    5.370    0.060    5.372    0.060 {method 'poll' of '_billiard.Connection' objects}
            1    3.515    3.515   17.008   17.008 /Users/csharp/local/projects/eventgen/lib/plugins/output/outputworker.py:69(real_run)
           88    3.188    0.036    3.188    0.036 {method 'recv' of '_billiard.Connection' objects}
      4400088    2.713    0.000    3.404    0.000 /Users/csharp/local/projects/eventgen/lib/plugins/output/devnull.py:16(<genexpr>)
           88    0.945    0.011    4.349    0.049 {method 'join' of 'str' objects}

With this, we can see that we're actually spending most of our time in the Queueing system.  I told you it sucked!  To get around this, we've implemented zeromq to allow for faster IPC between workers.  Lets test again after setting `queueing = zeromq` in `[global]` in default/eventgen.conf.

    csharp-mbp15:eventgen csharp$ python bin/eventgen.py tests/perf/eventgen.conf.perfwindbag
    2014-02-02 21:37:44,119 INFO Output Queue depth: 25  Generator Queue depth: 8509 Generators Per Sec: 13 Outputters Per Sec: 11
    2014-02-02 21:37:44,119 INFO Events/Sec: 560000.0 Kilobytes/Sec: 24609.375000 GB/Day: 2027.750015

There we go!  Actually scalable horizontal performance, exactly what we're looking for.

# Generator Types

Generators are written as [Plugins](Plugins.md).  These have varying performance characteristics depending on how they're written.  The default generator is the regex based replacement generator thats been available since Eventgen v1.  It is unfortunately slow.  It is very configurable, but that configurability comes at a cost in performance.  It is written entirely in Python, and it utilizes RegEx extensively which is slow.  

The replay generator (formerly mode=replay) is also slow, but for a different reason.  Because we're sequentially navigating through time, we can't easily multi-thread this operation, so thusly we can only run one copy of this at a time.

## Comparing three options

However, our plugin architecture is rich and we can easily hand-craft generators which will perform better.  For comparison purposes, we built a weblog based generator using three different approaches.

* Default Generator, Regex
** In this, we generate weblogs through the default generator, using regular expressions.  You can see the configs for this in `tests/perf/eventgen.conf.perfweblog`
* Hand-built Python Weblog Generator
** Here, we generate identical weblogs, but through a hand crafted Python generator preset in `lib/plugins/generator/weblog.py`
* C Weblog Generator
** And here, we wrap a little Python around a C-based Weblog generator.  The C generator is located in `lib/plugins/generator/cweblog.c` and the Python wrapper is in `lib/plugins/generator/cweblog.py`.  To run cweblog on your system, you'll need to customize some #define's for paths in cweblog.c and compile it (`gcc -c cweblog.c && gcc -o cweblog cweblog.o`).

## Testing

Okay, lets put this to the test and see what real world numbers look like.  All tests run on a Macbook air, two cores, with:

    [global]
    generatorWorkers = 2
    outputWorkers = 1
    threading = process
    queueing = zeromq

### Default Generator

    csharp-mbp15:eventgen csharp$ python bin/eventgen.py tests/perf/eventgen.conf.perfsampleweblog
    2014-02-02 21:42:35,299 INFO Output Queue depth: 0  Generator Queue depth: 44978 Generators Per Sec: 2 Outputters Per Sec: 3
    2014-02-02 21:42:35,299 INFO Events/Sec: 3030.0 Kilobytes/Sec: 1081.493359 GB/Day: 89.112307

### Hand-Crafted Python Generator

    csharp-mbp15:eventgen csharp$ python bin/eventgen.py tests/perf/eventgen.conf.perfweblog
    2014-02-02 21:45:50,142 INFO Output Queue depth: 0  Generator Queue depth: 28734 Generators Per Sec: 9 Outputters Per Sec: 9
    2014-02-02 21:45:50,142 INFO Events/Sec: 18000.0 Kilobytes/Sec: 6413.347266 GB/Day: 528.443531

### C Generator w/ Python Wrapper

    csharp-mbp15:eventgen csharp$ python bin/eventgen.py tests/perf/eventgen.conf.perfcweblog
    2014-02-02 21:46:42,575 INFO Output Queue depth: 2  Generator Queue depth: 28178 Generators Per Sec: 46 Outputters Per Sec: 46
    2014-02-02 21:46:42,575 INFO Events/Sec: 92846.4 Kilobytes/Sec: 32423.272656 GB/Day: 2671.595342

## Results & Conclusions

Obviously, C goes much faster.  For another 'I told you so', Python is slow.  From our original event generator using Regexs to a hand-crafted C based weblog generator, we've increased performance by a factor of 30x.  Thats awesome!  The middle ground may also be okay in terms of performance.  In fact, next, lets look at doing this on some bigger iron.

# Testing on a 24 core machine

Lastly, lets test on a bigger server sized machine and see what we can do.  We're going to test using these settings:

    [global]
    generatorWorkers = 20
    outputWorkers = 4
    threading = process
    queueing = zeromq

This will use most of the capacity of the machine for generating, and in my testing, does max out the machine at 100% CPU.  First, just to see on Events Per Second maximum, lets run the windbag:

    2014-02-02 21:55:20,351 INFO Output Queue depth: 407  Generator Queue depth: 7945 Generators Per Sec: 71 Outputters Per Sec: 29
    2014-02-02 21:55:20,352 INFO Events/Sec: 1470000.0 Kilobytes/Sec: 64599.609375 GB/Day: 5322.843790

Running the cweblog generator, lets see how far we can push the machine with 20 GeneratorWorkers and 4 OutputWorkers:

    2014-07-01 22:39:24,597 INFO module='main' sample='null': OutputQueueDepth=57  GeneratorQueueDepth=23730 GeneratorsPerSec=344 OutputtersPerSec=345
    2014-07-01 22:39:24,597 INFO module='main' sample='null': GlobalEventsPerSec=690745.2 KilobytesPerSec=241171.648633 GigabytesPerDay=19871.931497

We're outputting about 20TB a Day and keeping up with the output queue which is good.

# Removing the bottleneck

In this architecture, the primary bottleneck is serializing and deserializing the data between processes.  We added the reduce step of the outputqueue primarily to handle modular input and file outputs where we needed a limited number of things touching a file or outputting to stdout.  Where we can parallelize this work, we can remove the majority of the CPU bottleneck of passing data around between processes.

For this reason, in July of 2014, we added a config option to disable using the outputqueue.  In default/eventgen.conf, setting useOutputQueue to false or using `--disableOutputQueue` on the command line will output data directly from each GeneratorWorker rather than forcing the data back through the output queue.  Running the same performance test with the cweblog generator with 24 GeneratorWorkers and 0 OutputWorkers and useOutputQueue=false generates the following numbers:

    2014-07-01 22:43:01,232 INFO module='main' sample='null': GlobalEventsPerSec=17469130.2 KilobytesPerSec=6108727.259180 GigabytesPerDay=503343.615716

That's 503TB/day of output!  This is about 48GB/sec of output, which would half saturate a 100 gigabit network pipe.  This is more than enough output, so I think we can reasonably consider Eventgen to be able to generate more than enough data to saturate pretty much any instance from a single 24 core machine.