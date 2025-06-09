#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/wait.h>

/*
 *  Trois tests disponibles :
 *    - suspicious-mem : accès à /proc/self/mem
 *    - fork-bomb      : création de processus
 *    - file-ops       : création/suppression de fichiers
 */

void test_suspicious_mem(int count) {
    for (int i = 0; i < count; i++) {
        int fd = open("/proc/self/mem", O_RDWR);
        if (fd >= 0) {
            lseek(fd, (off_t)&fd, SEEK_SET);
            write(fd, "X", 1);
            close(fd);
        }
    }
}

void test_fork_bomb(int count) {
    for (int i = 0; i < count; i++) {
        if (fork() == 0)
            exit(0);
    }
    while (wait(NULL) > 0) ;
}

void test_file_ops(int count) {
    for (int i = 0; i < count; i++) {
        int fd = open("tempfile.txt", O_WRONLY | O_CREAT, 0644);
        if (fd >= 0) {
            write(fd, "Test", 4);
            close(fd);
            unlink("tempfile.txt");
        }
    }
}

void usage(const char *p) {
    fprintf(stderr,
        "Usage: %s <sequential|concurrent> <suspicious-mem|fork-bomb|file-ops> <iters>\n"
        "  sequential : exécute N fois le test choisi dans le même processus\n"
        "  concurrent : lance N processus enfants faisant 1 itération chacun\n"
        "  iters      : nombre d’itérations N\n",
        p);
    exit(1);
}

int main(int argc, char **argv) {
    if (argc != 4) usage(argv[0]);

    char *mode = argv[1], *type = argv[2];
    int it = atoi(argv[3]);
    if (it < 1) it = 1;

    if (strcmp(mode, "sequential") == 0) {
        if      (strcmp(type, "suspicious-mem") == 0) test_suspicious_mem(it);
        else if (strcmp(type, "fork-bomb")      == 0) test_fork_bomb(it);
        else if (strcmp(type, "file-ops")       == 0) test_file_ops(it);
        else usage(argv[0]);

    } else if (strcmp(mode, "concurrent") == 0) {
        if      (strcmp(type, "suspicious-mem") == 0) {
            for (int i = 0; i < it; i++)
                if (fork() == 0) { test_suspicious_mem(1); exit(0); }
        }
        else if (strcmp(type, "fork-bomb") == 0) {
            for (int i = 0; i < it; i++)
                if (fork() == 0) { test_fork_bomb(1); exit(0); }
        }
        else if (strcmp(type, "file-ops") == 0) {
            for (int i = 0; i < it; i++)
                if (fork() == 0) { test_file_ops(1); exit(0); }
        }
        else usage(argv[0]);

        while (wait(NULL) > 0) ;
    } else {
        usage(argv[0]);
    }
    return 0;
}
