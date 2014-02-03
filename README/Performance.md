# Intro

Eventgen v3 has been designed to scale, despite no small number of obstacles put in our way by Python.  Eventgen's original goals were primarily around making it simple for people to quickly build event generators for many different use cases without needing to resort to hand writing them every time.  This brings consistency and makes it simpler for others to come behind and support the work of others.  However, none of the earlier iterations really gave much thought to performance.

Prior to v3, Eventgen scaling was available only by increasing the number of samples Eventgen was running.  Each Sample was its own thread, and you could, up to a point, gain some additional scalability by adding more samples.  However, this approach quickly leads us to the first scalability blocker for Eventgen: its written in Python.

# Scaling, despite Python

I'm sure had either David or I considered that we'd eventually want to scale this thing, writing it in Python wouldn't have been the first choice.  Lets face it, Python is slow, and there's plenty of emperical evidence a quick Google away.   However, that doesn't stop us from being able to scale this thing.  There's a few things we must design around, which we'll explain in detail and will lead us to a quick walkthrough of some configuration tunables we've built int