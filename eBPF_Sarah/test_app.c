// test_app.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <math.h>

#define MIXED_WORK 100

void cpu(int iters) {
    volatile double x = 0;
    for (int i=0; i<iters; i++)
        for (int j=0; j<1000; j++)
            x += sqrt((double)j);
}

void file_read(int iters) {
    char buf[4096];
    for (int i=0; i<iters; i++) {
        int fd = open("/etc/passwd", O_RDONLY);
        if (fd>=0) { read(fd, buf, sizeof(buf)); close(fd); }
    }
}

void net_conn(int iters) {
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port   = htons(80),
        .sin_addr.s_addr = htonl(0x7F000001)
    };
    for (int i=0; i<iters; i++) {
        int s = socket(AF_INET, SOCK_STREAM, 0);
        if (s>=0) { connect(s,(struct sockaddr*)&addr,sizeof(addr)); close(s); }
    }
}

// 4) K=100 ouvertures par itération
void suspicious_mem(int iters) {
    for (int i=0; i<iters; i++) {
        for (int k=0; k<100; k++) {
            int fd = open("/proc/self/mem", O_RDWR);
            if (fd>=0) close(fd);
        }
    }
}

// 5) K=10 forks par itération
void fork_flood(int iters) {
    for (int i=0; i<iters; i++) {
        for (int k=0; k<10; k++) {
            pid_t pid = fork();
            if (pid==0) exit(0);
            wait(NULL);
        }
    }
}

void mixed(int iters) {
    for (int i=0; i<iters; i++) {
        cpu(1);
        file_read(1);
        net_conn(1);
    }
}

void benign_mixed(int iters) {
    for (int i=0; i<iters; i++) {
        file_read(1);
        fork_flood(1);  // 10 forks
    }
}

void malicious_mixed(int iters) {
    for (int i=0; i<iters; i++) {
        suspicious_mem(1);  // 100 opens
        fork_flood(1);      // 10 forks
    }
}

int main(int argc, char **argv) {
    if (argc!=3) {
        fprintf(stderr,"Usage: %s <type> <iters>\n",argv[0]);
        return 1;
    }
    int it = atoi(argv[2]);
    char *t = argv[1];
    if      (!strcmp(t,"cpu"))            cpu(it);
    else if (!strcmp(t,"file-read"))      file_read(it);
    else if (!strcmp(t,"net"))            net_conn(it);
    else if (!strcmp(t,"suspicious-mem")) suspicious_mem(it);
    else if (!strcmp(t,"fork-flood"))     fork_flood(it);
    else if (!strcmp(t,"mixed"))          mixed(it);
    else if (!strcmp(t,"benign-mixed"))   benign_mixed(it);
    else if (!strcmp(t,"malicious-mixed"))malicious_mixed(it);
    else { fprintf(stderr,"Unknown %s\n",t); return 1; }
    return 0;
}
