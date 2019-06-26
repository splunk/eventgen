# Intro

(This Document assumes you are already familiar with [Eventgen's architecture](ARCHITECTURE.md).  It is critical you read that document first.)

Eventgen v4 has been designed to scale, despite no small number of obstacles put in our way by Python.  Eventgen's original goals were primarily around making it simple for people to quickly build event generators for many different use cases without needing to resort to hand writing them every time.  This brings consistency and makes it simpler for others to come behind and support the work of others.  However, none of the earlier iterations really gave much thought to performance.

Prior to v4, Eventgen scaling was available only by increasing the number of samples Eventgen was running.  Each Sample was its own thread, and you could, up to a point, gain some additional scalability by adding more samples.  However, this approach quickly leads us to the first scalability blocker for Eventgen: its written in Python.

# Scaling, despite Python

I'm sure had either David or I considered that we'd eventually want to scale this thing, writing it in Python wouldn't have been the first choice.  Let's face it, Python is slow, and there's plenty of emperical evidence a quick Google away.   However, Python affords us a lot of advantages in developer productivity, and it is possible to write a minimal amount of code in other environments (C/Java/etc), write the majority in Python, and get good performance.  There's a few things we must design around, which we'll explain in detail and will lead us to a quick walkthrough of some configuration tunables we've built into Eventgen.

## The Global Interpreter Lock

The first obstacle to scaling a Python application is the Global Interpreter Lock.  Lots of information online, but long story short, only one Thread running Python code can be executed simultaneously.  Python functions written in C can run in different threads.  Threads in Python are lightweight, similar to OS threads, but they will only gain concurrency in the event that your Python program is primarily I/O bound or is spending a good portion of its time executing C-written python functions.

In the case of Eventgen, we do a non-insignificant amount of I/O, so our first step to scaling is to utilizing threading.  In Eventgen, we create a thread for each sample.  The sample acts as the master timer for that sample.  In the case of a queuable generator plugin, it will place an entry in the generator queue for generator workers to pick up.  With a non-queueable plugin, it will call the generator's `gen()` function directly.

## Growing beyond a single process

The GIL will limit our execution capacity eventually.  The next scaling capability Python affords us is the multiprocessing library.  Multiprocessing provides an API-compatible implementation of threading utilizing multiple processes instead of multiple threads to get around the GIL.  Because processes do not share memory, there are of course some limitations, but given our use case, multiprocessing works pretty well.  

We give the end user the choice between threading and processing via a tuneable in default/eventgen.conf under the [global] stanza:

    [global]
    threading = thread | process

For multiprocessing, set threading = process or pass `--multiprocess` on the command line.  This will cause eventgen to spin up a process for each generator worker and each output worker instead of a thread.  Samples will remain threads in the master process since they aren't really doing any work other than scheduling.

# Generator Types

Generators are written as [Plugins](Plugins.md).  These have varying performance characteristics depending on how they're written.  The default generator is the regex based replacement generator thats been available since Eventgen v1.  It is unfortunately slow.  It is very configurable, but that configurability comes at a cost in performance.  It is written entirely in Python, and it utilizes RegEx extensively which is slow.  

The replay generator (formerly mode=replay) is also slow, but for a different reason.  Because we're sequentially navigating through time, we can't easily multi-thread this operation, so thusly we can only run one copy of this at a time.

## Comparing two options

However, our plugin architecture is rich and we can easily hand-craft generators which will perform better.  For comparison purposes, we built a weblog based generator using two different approaches.

* Default Generator, Regex
** In this, we generate weblogs through the default generator, using regular expressions.  You can see the configs for this in `tests/perf/eventgen.conf.perfweblog`
* Hand-built Python Weblog Generator
** Here, we generate identical weblogs, but through a hand crafted Python generator preset in `lib/plugins/generator/weblog.py`

## Testing

Okay, let's put this to the test and see what real world numbers look like.  All tests run on eventgenx containers with the following .conf file:

    [global]
    generator = windbag
    earliest = now
    latest = now
    outputMode = httpevent
    httpeventServers = <Server Mapping>
    perDayVolume = <GB/day>

## Results & Conclusions

Using Splunk to track the event generation, we found that a single eventgenx container can generate at a maximum rate of 40-45 GB/day. Higher rates caused output queue backup, requiring more and more time to dump all events in a new interval. While this scenario is limited by the httpevent overhead, however Splunk allows us to track the real-time number of events and data size. More containers can be used in parallel to increase the throughput of generation on a single splunk instance.

We also wanted to compare the performance of the current Eventgen 6, compared to our legacy version 5. We tested 3 scenarios with varying amounts of token replacements on each version. All tests ran locally on a single 4-core, 16-gb memory machine and used the same httpevent output as the previous test. A stripped version of each config scenario and the samples used are located under tests/perf. Here are the results:

    1. Windbag generator with no token replacements
        Eventgen 5: 1.3 GB/day
        Eventgen 6: 26 GB/day
    2. Single timestamp token replacement
        Eventgen 5: 1.2 GB/day
        Eventgen 6: 24 GB/day
    3.  2 timestamp + 3 integer token replacements
        Eventgen 5: 1 GB/day
        Eventgen 6: 23 GB/day

Eventgen 6 shows a massive improvement to the overall generation rate. As we expected, using more token replacements in a sample also causes small slowdowns to the scenario's generation.

## Throughput with OutputCounter
In eventgenx, we provide a outputCounter to calculate the generaton rate. Turning on it can help you get throughput from eventgen directly. We have run a test on winbag sample with the following .conf file:

    [global]
    generator = windbag
    earliest = now
    latest = now
    outputMode = httpevent
    httpeventServers = <Server Mapping>
    perDayVolume = <GB/day>
    outputCounter = true

As a result, for a eventgen cluster with one server and one controller, we found that the output rate is about `455 KB/s`, and the output event count rate is `11361 events/s`

# Removing the bottleneck

In this architecture, the primary bottleneck is serializing and deserializing the data between processes.  We added the reduce step of the outputqueue primarily to handle modular input and file outputs where we needed a limited number of things touching a file or outputting to stdout.  Where we can parallelize this work, we can remove the majority of the CPU bottleneck of passing data around between processes.