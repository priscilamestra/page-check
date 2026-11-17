/*
 * Page Check STAGE36 — fail-closed Linux syscall boundary for Chromium.
 *
 * Restricts only the Chromium process tree. The trusted Python audit service
 * still fetches approved public resources using PublicHTTPTransport and sends
 * response bodies to Chromium through Playwright's existing pipe transport.
 *
 * This is defense in depth, NOT a container/network firewall. Do not mark
 * PAGECHECK_EGRESS_ISOLATED=1 based only on this launcher.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>

#if !defined(__linux__) || !defined(__x86_64__)
#error "Stage36 browser syscall filter must be reviewed for this architecture"
#endif

#if !defined(__NR_socket) || !defined(__NR_io_uring_setup)
#error "Required Linux syscalls are not defined"
#endif

/* Deny all new network socket families, permitting AF_UNIX for Chrome IPC.
 * Block io_uring_setup, which could otherwise create sockets asynchronously.
 * The filter is inherited on exec/fork and cannot be removed by Chromium.
 * X32 ABI syscalls are denied to prevent an alternate syscall entry path.
 */
static void install_guard(void) {
    const struct sock_filter code[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, (unsigned int)offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, (unsigned int)offsetof(struct seccomp_data, nr)),
        BPF_JUMP(BPF_JMP | BPF_JSET | BPF_K, 0x40000000U, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (unsigned int)__NR_io_uring_setup, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | (EPERM & SECCOMP_RET_DATA)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (unsigned int)__NR_socket, 0, 3),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, (unsigned int)offsetof(struct seccomp_data, args[0])),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AF_UNIX, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | (EPERM & SECCOMP_RET_DATA)),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    };
    const struct sock_fprog program = {
        .len = (unsigned short)(sizeof(code) / sizeof(code[0])),
        .filter = (struct sock_filter *)code,
    };
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0 ||
        prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) < 0) {
        perror("PAGECHECK_BROWSER_SECCOMP_UNAVAILABLE");
        exit(71);
    }
}

static int self_test(void) {
    install_guard();
    errno = 0;
    int fd4 = socket(AF_INET, SOCK_STREAM, 0);
    if (fd4 >= 0 || errno != EPERM) {
        if (fd4 >= 0) close(fd4);
        fputs("FAIL: IPv4 socket was not denied by seccomp\n", stderr);
        return 2;
    }
    puts("SECCOMP_IPV4_BLOCKED");

    errno = 0;
    int fd6 = socket(AF_INET6, SOCK_STREAM, 0);
    if (fd6 >= 0 || errno != EPERM) {
        if (fd6 >= 0) close(fd6);
        fputs("FAIL: IPv6 socket was not denied by seccomp\n", stderr);
        return 3;
    }
    puts("SECCOMP_IPV6_BLOCKED");

    int local = socket(AF_UNIX, SOCK_STREAM, 0);
    if (local < 0) {
        perror("FAIL: Unix-domain IPC socket unavailable");
        return 4;
    }
    close(local);
    puts("SECCOMP_UNIX_IPC_ALLOWED");

    puts("STAGE36_SYSCALL_GUARD_SELFTEST_PASSED");
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
        return self_test();
    }
    const char *browser = getenv("PAGECHECK_BROWSER_REAL_EXECUTABLE");
    if (!browser || browser[0] != '/' || argc < 2 ||
        strcmp(browser, argv[0]) == 0) {
        fputs("PAGECHECK_BROWSER_REAL_EXECUTABLE missing or invalid\n", stderr);
        return 70;
    }
    char **real_args = calloc((size_t)argc + 1U, sizeof(*real_args));
    if (!real_args) return 72;
    real_args[0] = (char *)browser;
    for (int i = 1; i < argc; ++i) real_args[i] = argv[i];
    real_args[argc] = NULL;
    install_guard();
    execv(browser, real_args);
    perror("PAGECHECK_CHROMIUM_LAUNCH_FAILED");
    return 73;
}
