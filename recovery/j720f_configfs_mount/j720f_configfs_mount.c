#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>

static void write_file(const char *path, const char *value)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);

    if (fd < 0)
        return;

    (void)write(fd, value, strlen(value));
    (void)write(fd, "\n", 1);
    close(fd);
}

static void mark(const char *name)
{
    char path[PATH_MAX];

    snprintf(path, sizeof(path), "/tmp/j720f-usb-%s", name);
    write_file(path, name);

    if (access("/cache", F_OK) == 0) {
        snprintf(path, sizeof(path), "/cache/j720f-usb-%s", name);
        write_file(path, name);
    }
}

static void mark_errno(const char *target_name, int error)
{
    char marker[128];

    snprintf(
        marker,
        sizeof(marker),
        "native-mount-%s-errno-%d",
        target_name,
        error
    );
    mark(marker);
}

static int proc_supports_configfs(void)
{
    FILE *fp;
    char line[256];

    fp = fopen("/proc/filesystems", "re");
    if (fp == NULL)
        return 0;

    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strstr(line, "configfs") != NULL) {
            fclose(fp);
            return 1;
        }
    }

    fclose(fp);
    return 0;
}

static int write_root_path(const char *target)
{
    write_file("/tmp/j720f-configfs-root", target);

    if (access("/cache", F_OK) == 0)
        write_file("/cache/j720f-configfs-root", target);

    return 0;
}

static int try_mount(const char *target, const char *target_name)
{
    char gadget_path[PATH_MAX];
    int saved_errno;

    if (mkdir(target, 0755) < 0 && errno != EEXIST) {
        mark_errno(target_name, errno);
        return -1;
    }

    snprintf(
        gadget_path,
        sizeof(gadget_path),
        "%s/usb_gadget",
        target
    );

    if (access(gadget_path, F_OK) == 0) {
        write_root_path(target);

        if (strcmp(target_name, "sys") == 0)
            mark("native-ready-sys");
        else
            mark("native-ready-config");

        return 0;
    }

    if (mount("configfs", target, "configfs", 0, NULL) < 0) {
        saved_errno = errno;

        if (saved_errno != EBUSY &&
            mount("none", target, "configfs", 0, NULL) < 0) {
            saved_errno = errno;

            if (saved_errno != EBUSY) {
                mark_errno(target_name, saved_errno);
                return -1;
            }
        }
    }

    if (access(gadget_path, F_OK) != 0) {
        if (strcmp(target_name, "sys") == 0)
            mark("native-mounted-no-gadget-sys");
        else
            mark("native-mounted-no-gadget-config");

        return -1;
    }

    write_root_path(target);

    if (strcmp(target_name, "sys") == 0)
        mark("native-ready-sys");
    else
        mark("native-ready-config");

    return 0;
}

int main(void)
{
    if (proc_supports_configfs())
        mark("native-proc-configfs");
    else
        mark("native-no-proc-configfs");

    if (try_mount("/sys/kernel/config", "sys") == 0)
        return 0;

    if (try_mount("/config", "config") == 0)
        return 0;

    mark("native-configfs-failed");
    return 1;
}
