#include <stdio.h>
#include <stdlib.h>
#include <sys/times.h>
#include <time.h>
#include <math.h>
#include <string.h>

#define BLOCK_SIZE 4096
#define TS_SIZE 50
#define INTERVAL 5

int main() {
    int         count;
    int         i;
    long        events;
    long        bytes;
    struct tms  timesout;
    long        ts;
    long        lastts;
    float       kbsec;
    float       kbsecavg;
    float       gbday;
    float       gbdayavg;
    char        *buf;
    char        *tsbuf;
    int         result;
    time_t      curtime;
    struct tm   *loctime;
    int         loopcount;

    lastts = times(&timesout);
    loopcount = 0;

    while (1) {
        buf = malloc(BLOCK_SIZE);
        tsbuf = malloc(TS_SIZE);

        result = fread(buf, 1, BLOCK_SIZE, stdin);
        if (result != BLOCK_SIZE) { 
            fputs ("Error reading from stdin", stderr); 
            exit (1);
        }

        count = 1;
        for (i=0;i<BLOCK_SIZE;i++) {
            if (buf[i] == '\n') {
                count++;
            }
        }
        // if (strncmp(&buf[BLOCK_SIZE-1], "\n", 1)) {
        //     events += count-1;  /* Unless the last character is a newline, we shouldn't count the last event
        //                             It will be picked up by the next iteration */
        // }
        events += count-1;
        bytes += BLOCK_SIZE;

        loopcount++;

        // Only check the time every 100 iterations
        if (loopcount % 100 == 0) {
            loopcount = 0;

            ts = time(NULL);
            // ts = (int)round(ts/1000);
            if (ts != lastts && ts % INTERVAL == 0 ) {
                // printf("TS: %ld\n", ts);
                lastts = ts;
                kbsec = bytes/INTERVAL/1024;
                gbday = kbsec * 60 * 60 * 24 /1024 / 1024;
                kbsecavg = (kbsecavg + kbsec) / 2;
                gbdayavg = (gbdayavg + gbday) / 2;

                loctime = localtime(&ts);

                strftime(tsbuf, TS_SIZE, "%Y-%m-%d %H:%M:%S", loctime);

                printf("%s Events/Sec: %1f Kilobytes/Sec: %1f GB/Day: %1f\n", tsbuf, (float)(events / INTERVAL), kbsec, gbday);

                bytes = 0;
                events = 0;
            }
        }

        free(buf);
        free(tsbuf);
    }
}
