#include <stdio.h>
#include <stdlib.h>
#include <sys/times.h>
#include <time.h>
#include <math.h>
#include <string.h>

#define DEBUG 0
#define IPS_PATH "/Users/csharp/local/projects/eventgen/tests/perf/weblog/external_ips.sample"
#define WEBHOSTS_PATH "/Users/csharp/local/projects/eventgen/tests/perf/weblog/webhosts.sample"
#define USERAGENTS_PATH "/Users/csharp/local/projects/eventgen/tests/perf/weblog/useragents.sample"
#define WEBSERVERSTATUS_PATH "/Users/csharp/local/projects/eventgen/tests/perf/weblog/webserverstatus.sample"

typedef struct itemslist {
    char *item;
    struct itemslist *next;
} itemslist;

typedef struct items {
    int count;
    itemslist *l;
} items;


void additem(items *i, char *item) {
    itemslist *newitem;
    itemslist *cur;

    newitem = malloc(sizeof(itemslist));
    newitem->next = NULL;
    newitem->item = item;
    // First item
    if (i->count == 0) {
        i->l = newitem;
    // Not first item, loop till the end of the list
    // and add item to the end
    } else {
        cur = i->l;
        while (cur->next != NULL) {
            cur = cur->next;
        }
        cur->next = newitem;
    }
    i->count++;
}

char *getitem(items *i, int idx) {
    itemslist *il = i->l;
    int x = 0;

    for (x=0; x < idx; x++) {
        if (il->next != NULL) {
            il = il->next;
        }
    }
    if (DEBUG) {
        printf("getitem returning: %s\n", il->item);
    }
    return il->item;
}

items *loadfile(char *file) {
    FILE *fp;
    char *line = NULL;
    size_t len = 0;
    ssize_t read;
    items *i;

    if (DEBUG) {
        printf("Loading file: %s\n", file);
    }
    i = malloc(sizeof(items));

    fp = fopen(file, "r");
    while ((read = getline(&line, &len, fp)) != -1) {
        // Trim newline
        if (line[strlen(line)-1] == '\n') {
            line[strlen(line)-1] = '\0';
        }
        if (DEBUG) {
            //printf("Adding line: %s\n", line);
        }
        additem(i, strdup(line));
    }

    return i;
} 

int main() {

    // Read from stdin a line containing a tuple of three values
    // Count;EarliestTsEpochTime;LatestTsEpochTime

    char *line = NULL, *origline = NULL;
    size_t len = 0;
    ssize_t read;
    char *counts;
    int count;
    char *earliest_tss;
    long earliest_ts;
    char *latest_tss;
    long latest_ts;

    items *ips;
    items *webhosts;
    items *useragents;
    items *webserverstatuses;

    char *ip;
    char *webhost;
    char *useragent;
    char *webserverstatus;

    int ipidx = 0;
    int webhostidx = 0;
    int useragentidx = 0;
    int webserverstatusidx = 0;

    struct tm *loctime;

    int sizestr = 0;
    int durationstr = 0;

    int i = 0;
    char *curtime;

    while ((read = getline(&line, &len, stdin)) != -1) {
        if (DEBUG) {
            printf("Retrieved line of length %zu :\n", read);
            printf("%s", line);
        }

        origline = line;
        counts = strdup(strsep(&line, ";"));
        earliest_tss = strdup(strsep(&line, ";"));
        latest_tss = strdup(line);
        // Trim newline
        latest_tss[strlen(latest_tss)-1] = '\0';

        if (DEBUG) {
            printf("Counts: %s EarliestTSS: %s LatestTSS: %s\n", counts, earliest_tss, latest_tss);
        }

        count = atoi(counts);
        earliest_ts = atol(earliest_tss);
        latest_ts = atol(latest_tss);

        if (DEBUG) {
            printf("Count: %d EarliestTS: %d LatestTS: %d\n", count, earliest_ts, latest_ts);
        }
        if (count > 0) {
            break;
        }

    }

    free(origline);

    // Allocate objects
    ips = malloc(sizeof(items));
    webhosts = malloc(sizeof(items));
    useragents = malloc(sizeof(items));
    webserverstatuses = malloc(sizeof(items));

    // Initialize values
    ips->count = 0;
    ips->l = NULL;
    webhosts->count = 0;
    webhosts->l = NULL;
    useragents->count = 0;
    useragents->l = NULL;
    webserverstatuses->count = 0;
    webserverstatuses->l = NULL;

    // Read files into memory
    ips = loadfile(IPS_PATH);
    webhosts = loadfile(WEBHOSTS_PATH);
    useragents = loadfile(USERAGENTS_PATH);
    webserverstatuses = loadfile(WEBSERVERSTATUS_PATH);

    if (DEBUG) {
        printf("Ips Count: %d Webhosts Count: %d User Agents count: %d Web Server Statuses Count: %d\n", ips->count, webhosts->count, useragents->count, webserverstatuses->count);
    }


    srand(time(NULL));
    curtime = malloc(50);
    // Generate events
    for (i=0; i < count; i++) {
        // Get random selections to substitute in
        ipidx = rand() % ips->count;
        webhostidx = rand() % webhosts->count;
        useragentidx = rand() % useragents->count;
        webserverstatusidx = rand() % webserverstatuses->count;

        if (DEBUG) {
            printf("IPidx: %d Webhostidx: %d Useragentidx: %d Webserverstatusidx: %d\n", ipidx, webhostidx, useragentidx, webserverstatusidx);
        }

        ip = getitem(ips, ipidx);
        webhost = getitem(webhosts, webhostidx);
        useragent = getitem(useragents, useragentidx);
        webserverstatus = getitem(webserverstatuses, webserverstatusidx);

        if (DEBUG) {
            printf("IP: %s\nWebhost: %s\nUseragent: %s\nWebserverstatus: %s\n", ip, webhost, useragent, webserverstatus);
        }

        loctime = localtime((time_t*)&latest_ts);
        if (DEBUG) {
            printf("Current time asctime: %s\n", asctime(loctime));
        }

        curtime = malloc(100);
        strftime(curtime, 100, "%d/%b/%Y %H:%M:%S", loctime);

        if (DEBUG) {
            printf("Current time: %s\n", curtime);
        }

        sizestr = rand() % 1000;
        durationstr = rand() % 2000;

        printf("%s %s - - [%s] \"GET /product.screen?product_id=HolyGouda&JSESSIONID=SD3SL1FF7ADFF8 HTTP 1.1\" %s %d \"http://shop.buttercupgames.com/cart.do?action=view&itemId=HolyGouda\" \"%s\" %d\n",
                ip, webhost, curtime, webserverstatus, sizestr, useragent, durationstr);
        free(curtime);
    }

    // We should clean up here and free ram we've allocated, but just exit instead
    exit(EXIT_SUCCESS);
}
