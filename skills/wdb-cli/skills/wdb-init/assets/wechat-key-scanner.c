/*
 * WDB Pro local WeChat key scanner for macOS.
 *
 * Adapted from huohuoer/wechat-cli's find_all_keys_macos.c and shared key
 * verification logic (Apache-2.0). Changes: account-scoped database discovery,
 * support for every current WeChat key-candidate shape, SQLCipher page-HMAC
 * verification, multi-process scanning, and machine-readable diagnostics.
 * The WeChat 4.1+ login-capture and per-database derivation flow is based on
 * TANGandXUE/wcdb-key-tool (MIT). This implementation uses native Mach hardware
 * breakpoints so end users do not need LLDB or Command Line Tools.
 */
#define _XOPEN_SOURCE 700
#define _DARWIN_C_SOURCE 1

#include <CommonCrypto/CommonHMAC.h>
#include <CommonCrypto/CommonKeyDerivation.h>
#include <CommonCrypto/CommonCryptoError.h>
#include <dirent.h>
#include <dlfcn.h>
#include <errno.h>
#include <ftw.h>
#include <mach/exc.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/thread_act.h>
#if defined(__x86_64__)
#include <mach/i386/thread_status.h>
#elif defined(__arm64__)
#include <mach/arm/thread_status.h>
#endif
#include <stdint.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/sysctl.h>
#include <time.h>
#include <unistd.h>

#define MAX_CANDIDATES 512
#define MAX_DBS 512
#define MAX_WECHAT_PIDS 32
#define KEY_HEX_LEN 64
#define SALT_HEX_LEN 32
#define MIN_PATTERN_HEX_LEN 64
#define MAX_PATTERN_HEX_LEN 192
#define SQLCIPHER_PAGE_SIZE 4096
#define SQLCIPHER_HMAC_OFFSET 4032
#define CHUNK_SIZE (2 * 1024 * 1024)
#define PASSPHRASE_SIZE 32
#define PASSPHRASE_ROUNDS 256000
#define DEFAULT_CAPTURE_TIMEOUT_SECONDS 180

static unsigned char g_db_pages[MAX_DBS][SQLCIPHER_PAGE_SIZE];
static char g_db_salts[MAX_DBS][SALT_HEX_LEN + 1];
static char g_db_paths[MAX_DBS][1024];
static char g_db_keys[MAX_DBS][KEY_HEX_LEN + 1];
static char g_seen_candidates[MAX_CANDIDATES][MAX_PATTERN_HEX_LEN + 1];
static const char *g_db_root = NULL;
static int g_db_count = 0;
static int g_seen_candidate_count = 0;
static size_t g_candidate_count = 0;
static size_t g_unique_candidate_count = 0;

static mach_port_t g_capture_task = MACH_PORT_NULL;
static mach_vm_address_t g_breakpoint_address = 0;
static unsigned char g_captured_passphrase[PASSPHRASE_SIZE];
static int g_capture_candidate_ready = 0;
static int g_capture_exception_handled = 0;
static char g_capture_diagnostic[256] = "not_started";
static const exception_mask_t g_capture_exception_mask = EXC_MASK_BREAKPOINT;

static void set_capture_diagnostic(const char *format, ...) {
    va_list arguments;
    va_start(arguments, format);
    vsnprintf(g_capture_diagnostic, sizeof(g_capture_diagnostic), format, arguments);
    va_end(arguments);
}
static int is_hex(unsigned char value) {
    return (value >= '0' && value <= '9') ||
           (value >= 'a' && value <= 'f') ||
           (value >= 'A' && value <= 'F');
}

static void lowercase_hex(char *value) {
    for (; *value; value++) {
        if (*value >= 'A' && *value <= 'F') *value += 32;
    }
}

static int hex_to_bytes(const char *hex, unsigned char *output, size_t output_size) {
    for (size_t index = 0; index < output_size; index++) {
        unsigned char high = (unsigned char)hex[index * 2];
        unsigned char low = (unsigned char)hex[index * 2 + 1];
        if (!is_hex(high) || !is_hex(low)) return -1;
        high = (unsigned char)(high <= '9' ? high - '0' : (high | 32) - 'a' + 10);
        low = (unsigned char)(low <= '9' ? low - '0' : (low | 32) - 'a' + 10);
        output[index] = (unsigned char)((high << 4) | low);
    }
    return 0;
}

static void bytes_to_hex(const unsigned char *bytes, size_t size, char *output) {
    static const char alphabet[] = "0123456789abcdef";
    for (size_t index = 0; index < size; index++) {
        output[index * 2] = alphabet[bytes[index] >> 4];
        output[index * 2 + 1] = alphabet[bytes[index] & 0x0f];
    }
    output[size * 2] = '\0';
}

static int calculate_page_hmac(const char *key_hex, const unsigned char *page,
                               unsigned char output[CC_SHA512_DIGEST_LENGTH]) {
    unsigned char encryption_key[32];
    unsigned char mac_salt[16];
    unsigned char mac_key[32];
    unsigned char hmac_input[SQLCIPHER_HMAC_OFFSET - 16 + 4];
    if (hex_to_bytes(key_hex, encryption_key, sizeof(encryption_key)) != 0) return -1;

    for (size_t index = 0; index < sizeof(mac_salt); index++) {
        mac_salt[index] = (unsigned char)(page[index] ^ 0x3a);
    }
    int result = CCKeyDerivationPBKDF(
        kCCPBKDF2, (const char *)encryption_key, sizeof(encryption_key),
        mac_salt, sizeof(mac_salt), kCCPRFHmacAlgSHA512, 2,
        mac_key, sizeof(mac_key));
    if (result != kCCSuccess) return -1;

    memcpy(hmac_input, page + 16, SQLCIPHER_HMAC_OFFSET - 16);
    hmac_input[SQLCIPHER_HMAC_OFFSET - 16] = 1;
    hmac_input[SQLCIPHER_HMAC_OFFSET - 15] = 0;
    hmac_input[SQLCIPHER_HMAC_OFFSET - 14] = 0;
    hmac_input[SQLCIPHER_HMAC_OFFSET - 13] = 0;
    CCHmac(kCCHmacAlgSHA512, mac_key, sizeof(mac_key),
           hmac_input, sizeof(hmac_input), output);
    return 0;
}

static int verify_key_for_database(const char *key_hex, int db_index) {
    unsigned char digest[CC_SHA512_DIGEST_LENGTH];
    if (calculate_page_hmac(key_hex, g_db_pages[db_index], digest) != 0) return 0;
    return memcmp(digest, g_db_pages[db_index] + SQLCIPHER_HMAC_OFFSET,
                  CC_SHA512_DIGEST_LENGTH) == 0;
}

static int read_database_page(const char *path, unsigned char *page, char *salt) {
    FILE *file = fopen(path, "rb");
    if (!file) return -1;
    size_t count = fread(page, 1, SQLCIPHER_PAGE_SIZE, file);
    fclose(file);
    if (count != SQLCIPHER_PAGE_SIZE || memcmp(page, "SQLite format 3", 15) == 0) return -1;
    bytes_to_hex(page, 16, salt);
    return 0;
}

static int collect_database(const char *path, const struct stat *info, int type, struct FTW *walk) {
    (void)info;
    (void)walk;
    size_t length = strlen(path);
    if (type != FTW_F || length < 3 || strcmp(path + length - 3, ".db") != 0 || g_db_count >= MAX_DBS) return 0;
    if (read_database_page(path, g_db_pages[g_db_count], g_db_salts[g_db_count]) != 0) return 0;

    const char *relative = path;
    size_t root_length = strlen(g_db_root);
    if (strncmp(path, g_db_root, root_length) == 0) {
        relative = path + root_length;
        if (*relative == '/') relative++;
    }
    snprintf(g_db_paths[g_db_count], sizeof(g_db_paths[g_db_count]), "%s", relative);
    g_db_count++;
    return 0;
}

static int find_wechat_pids(pid_t *pids, int capacity) {
    if (capacity <= 0) return 0;
    const char *target_pid = getenv("WDB_WECHAT_PID");
    if (target_pid && *target_pid) {
        char *end = NULL;
        long parsed_pid = strtol(target_pid, &end, 10);
        if (end != target_pid && *end == '\0' && parsed_pid > 0 &&
            parsed_pid <= INT32_MAX && kill((pid_t)parsed_pid, 0) == 0) {
            pids[0] = (pid_t)parsed_pid;
            return 1;
        }
        return 0;
    }

    FILE *process = popen("(/usr/bin/pgrep -x WeChat; /usr/bin/pgrep -x Weixin) | /usr/bin/sort -nu", "r");
    if (!process) return 0;
    char buffer[64];
    int count = 0;
    while (count < capacity && fgets(buffer, sizeof(buffer), process)) {
        pid_t pid = (pid_t)atoi(buffer);
        if (pid > 0) pids[count++] = pid;
    }
    pclose(process);
    return count;
}

static int process_uid(pid_t pid, uid_t *uid) {
    int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_PID, pid};
    struct kinfo_proc process_info;
    size_t process_info_size = sizeof(process_info);
    memset(&process_info, 0, sizeof(process_info));
    if (sysctl(mib, 4, &process_info, &process_info_size, NULL, 0) != 0 ||
        process_info_size == 0) {
        return -1;
    }
    *uid = process_info.kp_eproc.e_ucred.cr_uid;
    return 0;
}

static int probe_task_access(pid_t pid) {
    uid_t target_uid = (uid_t)-1;
    (void)process_uid(pid, &target_uid);

    mach_port_t task = MACH_PORT_NULL;
    kern_return_t result = task_for_pid(mach_task_self(), pid, &task);
    if (result != KERN_SUCCESS) {
        fprintf(stderr,
                "TASK_ACCESS_DENIED:pid=%d,caller_uid=%u,target_uid=%u,kr=%d\n",
                pid, (unsigned int)geteuid(), (unsigned int)target_uid, result);
        return 77;
    }

    printf("TASK_ACCESS_READY:pid=%d,caller_uid=%u,target_uid=%u\n",
           pid, (unsigned int)geteuid(), (unsigned int)target_uid);
    mach_port_deallocate(mach_task_self(), task);
    return 0;
}

static int all_databases_matched(void) {
    for (int index = 0; index < g_db_count; index++) {
        if (g_db_keys[index][0] == '\0') return 0;
    }
    return g_db_count > 0;
}

static int remember_candidate(const char *candidate) {
    for (int index = 0; index < g_seen_candidate_count; index++) {
        if (strcmp(g_seen_candidates[index], candidate) == 0) return 0;
    }
    if (g_seen_candidate_count < MAX_CANDIDATES) {
        snprintf(g_seen_candidates[g_seen_candidate_count],
                 sizeof(g_seen_candidates[g_seen_candidate_count]), "%s", candidate);
        g_seen_candidate_count++;
    }
    g_unique_candidate_count++;
    return 1;
}

static void apply_key_to_all_databases(const char *key) {
    for (int db_index = 0; db_index < g_db_count; db_index++) {
        if (g_db_keys[db_index][0] == '\0' && verify_key_for_database(key, db_index)) {
            snprintf(g_db_keys[db_index], sizeof(g_db_keys[db_index]), "%s", key);
        }
    }
}

static void match_candidate(char *candidate, size_t length) {
    lowercase_hex(candidate);
    if (!remember_candidate(candidate)) return;

    char key[KEY_HEX_LEN + 1];
    memcpy(key, candidate, KEY_HEX_LEN);
    key[KEY_HEX_LEN] = '\0';

    if (length == KEY_HEX_LEN) {
        apply_key_to_all_databases(key);
        return;
    }

    char salt[SALT_HEX_LEN + 1];
    memcpy(salt, candidate + length - SALT_HEX_LEN, SALT_HEX_LEN);
    salt[SALT_HEX_LEN] = '\0';
    int matched = 0;
    for (int db_index = 0; db_index < g_db_count; db_index++) {
        if (g_db_keys[db_index][0] != '\0' || strcmp(g_db_salts[db_index], salt) != 0) continue;
        if (verify_key_for_database(key, db_index)) {
            snprintf(g_db_keys[db_index], sizeof(g_db_keys[db_index]), "%s", key);
            matched = 1;
        }
    }
    if (matched) apply_key_to_all_databases(key);
}

static void process_memory_buffer(const unsigned char *buffer, size_t size) {
    for (size_t offset = 0; offset + MIN_PATTERN_HEX_LEN + 3 <= size; offset++) {
        if (buffer[offset] != 'x' || buffer[offset + 1] != '\'') continue;
        size_t start = offset + 2;
        size_t length = 0;
        while (start + length < size && length <= MAX_PATTERN_HEX_LEN &&
               is_hex(buffer[start + length])) {
            length++;
        }
        if (length < MIN_PATTERN_HEX_LEN || length > MAX_PATTERN_HEX_LEN ||
            start + length >= size || buffer[start + length] != '\'') continue;

        char candidate[MAX_PATTERN_HEX_LEN + 1];
        memcpy(candidate, buffer + start, length);
        candidate[length] = '\0';
        g_candidate_count++;
        match_candidate(candidate, length);
        offset = start + length;
    }
}

static void scan_wechat_task(mach_port_t task, size_t *region_count, uint64_t *byte_count) {
    mach_vm_address_t address = 0;
    while (!all_databases_matched()) {
        mach_vm_size_t size = 0;
        vm_region_basic_info_data_64_t info;
        mach_msg_type_number_t info_count = VM_REGION_BASIC_INFO_COUNT_64;
        mach_port_t object_name = MACH_PORT_NULL;
        kern_return_t result = mach_vm_region(task, &address, &size, VM_REGION_BASIC_INFO_64,
                                              (vm_region_info_t)&info, &info_count, &object_name);
        if (result != KERN_SUCCESS) break;
        if (object_name != MACH_PORT_NULL) mach_port_deallocate(mach_task_self(), object_name);
        if (size == 0) {
            address++;
            continue;
        }

        mach_vm_address_t region_end = address + size;
        if ((info.protection & VM_PROT_READ) != 0 && (info.protection & VM_PROT_EXECUTE) == 0) {
            mach_vm_address_t cursor = address;
            while (cursor < region_end && !all_databases_matched()) {
                mach_vm_size_t chunk_size = region_end - cursor;
                if (chunk_size > CHUNK_SIZE) chunk_size = CHUNK_SIZE;
                vm_offset_t data = 0;
                mach_msg_type_number_t data_count = 0;
                result = mach_vm_read(task, cursor, chunk_size, &data, &data_count);
                if (result == KERN_SUCCESS) {
                    process_memory_buffer((const unsigned char *)data, data_count);
                    (*region_count)++;
                    *byte_count += data_count;
                    mach_vm_deallocate(mach_task_self(), data, data_count);
                }
                if (cursor + chunk_size >= region_end) break;
                const mach_vm_size_t overlap = MAX_PATTERN_HEX_LEN + 3;
                cursor += chunk_size > overlap ? chunk_size - overlap : chunk_size;
            }
        }
        if (address + size <= address) break;
        address += size;
    }
}

extern boolean_t exc_server(mach_msg_header_t *request, mach_msg_header_t *reply);

static int read_target_memory(mach_port_t task, mach_vm_address_t address,
                              void *output, mach_vm_size_t size) {
    mach_vm_size_t copied = 0;
    kern_return_t result = mach_vm_read_overwrite(
        task, address, size, (mach_vm_address_t)output, &copied);
    return result == KERN_SUCCESS && copied == size ? 0 : -1;
}

static int configure_thread_breakpoint(thread_act_t thread, int enabled) {
#if defined(__x86_64__)
    x86_debug_state64_t state;
    mach_msg_type_number_t state_count = x86_DEBUG_STATE64_COUNT;
    kern_return_t state_result = thread_get_state(
        thread, x86_DEBUG_STATE64, (thread_state_t)&state, &state_count);
    if (state_result != KERN_SUCCESS) {
        set_capture_diagnostic("x86_debug_state_read_failed:kr=%d", state_result);
        return -1;
    }
    if (enabled) {
        state.__dr0 = g_breakpoint_address;
        state.__dr7 = (state.__dr7 & ~0xf0003ULL) | 1ULL;
    } else if (state.__dr0 == g_breakpoint_address) {
        state.__dr0 = 0;
        state.__dr7 &= ~0xf0003ULL;
    }
    state_result = thread_set_state(
        thread, x86_DEBUG_STATE64, (thread_state_t)&state, state_count);
    if (state_result != KERN_SUCCESS) {
        set_capture_diagnostic("x86_debug_state_write_failed:kr=%d", state_result);
        return -1;
    }
    return 0;
#elif defined(__arm64__)
    arm_debug_state64_t state;
    mach_msg_type_number_t state_count = ARM_DEBUG_STATE64_COUNT;
    if (thread_get_state(thread, ARM_DEBUG_STATE64,
                         (thread_state_t)&state, &state_count) != KERN_SUCCESS) {
        return -1;
    }
    if (enabled) {
        state.__bvr[0] = g_breakpoint_address;
        state.__bcr[0] = 0x1e5;
    } else if (state.__bvr[0] == g_breakpoint_address) {
        state.__bvr[0] = 0;
        state.__bcr[0] = 0;
    }
    return thread_set_state(thread, ARM_DEBUG_STATE64,
                            (thread_state_t)&state, state_count) == KERN_SUCCESS ? 0 : -1;
#else
#error Unsupported macOS architecture
#endif
}

static int configure_task_breakpoints(mach_port_t task, int enabled) {
    thread_act_array_t threads = NULL;
    mach_msg_type_number_t thread_count = 0;
    if (task_threads(task, &threads, &thread_count) != KERN_SUCCESS) return -1;
    int configured = 0;
    for (mach_msg_type_number_t index = 0; index < thread_count; index++) {
        if (configure_thread_breakpoint(threads[index], enabled) == 0) configured++;
        mach_port_deallocate(mach_task_self(), threads[index]);
    }
    mach_vm_deallocate(mach_task_self(), (mach_vm_address_t)threads,
                       thread_count * sizeof(thread_act_t));
    return configured > 0 ? 0 : -1;
}

static int salt_matches_database(const unsigned char salt[16]) {
    for (int index = 0; index < g_db_count; index++) {
        if (memcmp(g_db_pages[index], salt, 16) == 0) return 1;
    }
    return 0;
}

kern_return_t catch_exception_raise(
    mach_port_t exception_port, mach_port_t thread, mach_port_t task,
    exception_type_t exception, exception_data_t code,
    mach_msg_type_number_t code_count) {
    (void)exception_port;
    (void)task;
    (void)code;
    (void)code_count;
    if (exception != EXC_BREAKPOINT) return KERN_FAILURE;

    mach_vm_address_t password_address = 0;
    mach_vm_address_t salt_address = 0;
    uint64_t password_length = 0;
    uint64_t salt_length = 0;
    uint64_t rounds = 0;
    int hit = 0;

#if defined(__x86_64__)
    x86_thread_state64_t state;
    mach_msg_type_number_t state_count = x86_THREAD_STATE64_COUNT;
    if (thread_get_state(thread, x86_THREAD_STATE64,
                         (thread_state_t)&state, &state_count) != KERN_SUCCESS) {
        return KERN_FAILURE;
    }
    hit = state.__rip == g_breakpoint_address + 1;
    if (!hit) hit = state.__rip == g_breakpoint_address;
    if (hit) {
        password_address = state.__rsi;
        password_length = state.__rdx;
        salt_address = state.__rcx;
        salt_length = state.__r8;
        (void)read_target_memory(g_capture_task, state.__rsp + 8, &rounds, sizeof(rounds));
        if (configure_thread_breakpoint(thread, 0) != 0) return KERN_FAILURE;
    }
#elif defined(__arm64__)
    arm_thread_state64_t state;
    mach_msg_type_number_t state_count = ARM_THREAD_STATE64_COUNT;
    if (thread_get_state(thread, ARM_THREAD_STATE64,
                         (thread_state_t)&state, &state_count) != KERN_SUCCESS) {
        return KERN_FAILURE;
    }
    uintptr_t pc = arm_thread_state64_get_pc(state);
    hit = pc == g_breakpoint_address || pc == g_breakpoint_address + 4;
    if (hit) {
        password_address = state.__x[1];
        password_length = state.__x[2];
        salt_address = state.__x[3];
        salt_length = state.__x[4];
        rounds = state.__x[6];
        if (configure_thread_breakpoint(thread, 0) != 0) return KERN_FAILURE;
    }
#endif

    if (!hit) return KERN_FAILURE;
    g_capture_exception_handled = 1;
    if (password_length == PASSPHRASE_SIZE && salt_length == 16 &&
        rounds == PASSPHRASE_ROUNDS) {
        unsigned char salt[16];
        if (read_target_memory(g_capture_task, salt_address, salt, sizeof(salt)) == 0 &&
            salt_matches_database(salt) &&
            read_target_memory(g_capture_task, password_address,
                               g_captured_passphrase, sizeof(g_captured_passphrase)) == 0) {
            g_capture_candidate_ready = 1;
        }
    }
    return KERN_SUCCESS;
}

kern_return_t catch_exception_raise_state(
    mach_port_t exception_port, exception_type_t exception,
    const exception_data_t code, mach_msg_type_number_t code_count,
    int *flavor, const thread_state_t old_state,
    mach_msg_type_number_t old_state_count, thread_state_t new_state,
    mach_msg_type_number_t *new_state_count) {
    (void)exception_port;
    (void)exception;
    (void)code;
    (void)code_count;
    (void)flavor;
    (void)old_state;
    (void)old_state_count;
    (void)new_state;
    (void)new_state_count;
    return KERN_FAILURE;
}

kern_return_t catch_exception_raise_state_identity(
    mach_port_t exception_port, mach_port_t thread, mach_port_t task,
    exception_type_t exception, exception_data_t code,
    mach_msg_type_number_t code_count, int *flavor,
    thread_state_t old_state, mach_msg_type_number_t old_state_count,
    thread_state_t new_state, mach_msg_type_number_t *new_state_count) {
    (void)exception_port;
    (void)thread;
    (void)task;
    (void)exception;
    (void)code;
    (void)code_count;
    (void)flavor;
    (void)old_state;
    (void)old_state_count;
    (void)new_state;
    (void)new_state_count;
    return KERN_FAILURE;
}

static void restore_exception_ports(
    mach_port_t task, exception_mask_t *masks, mach_port_t *ports,
    exception_behavior_t *behaviors, thread_state_flavor_t *flavors,
    mach_msg_type_number_t count) {
    for (mach_msg_type_number_t index = 0; index < count; index++) {
        task_set_exception_ports(task, masks[index], ports[index],
                                 behaviors[index], flavors[index]);
    }
}

static int derive_keys_from_passphrase(const unsigned char passphrase[PASSPHRASE_SIZE]) {
    int matched = 0;
    memset(g_db_keys, 0, sizeof(g_db_keys));
    for (int db_index = 0; db_index < g_db_count; db_index++) {
        unsigned char encryption_key[32];
        int result = CCKeyDerivationPBKDF(
            kCCPBKDF2, (const char *)passphrase, PASSPHRASE_SIZE,
            g_db_pages[db_index], 16, kCCPRFHmacAlgSHA512,
            PASSPHRASE_ROUNDS, encryption_key, sizeof(encryption_key));
        if (result != kCCSuccess) continue;
        char key_hex[KEY_HEX_LEN + 1];
        bytes_to_hex(encryption_key, sizeof(encryption_key), key_hex);
        if (verify_key_for_database(key_hex, db_index)) {
            snprintf(g_db_keys[db_index], sizeof(g_db_keys[db_index]), "%s", key_hex);
            matched++;
        }
    }
    return matched;
}

static int capture_passphrase_from_task(
    mach_port_t task, int timeout_seconds,
    unsigned char output[PASSPHRASE_SIZE]) {
    set_capture_diagnostic("not_started");
    void *symbol = dlsym(RTLD_DEFAULT, "CCKeyDerivationPBKDF");
    if (!symbol) {
        set_capture_diagnostic("symbol_not_found");
        return -2;
    }

    g_capture_task = task;
    g_breakpoint_address = (mach_vm_address_t)symbol;
    g_capture_candidate_ready = 0;
    g_capture_exception_handled = 0;
    memset(g_captured_passphrase, 0, sizeof(g_captured_passphrase));

    exception_mask_t masks[EXC_TYPES_COUNT];
    mach_port_t ports[EXC_TYPES_COUNT];
    exception_behavior_t behaviors[EXC_TYPES_COUNT];
    thread_state_flavor_t flavors[EXC_TYPES_COUNT];
    mach_msg_type_number_t port_count = EXC_TYPES_COUNT;
    kern_return_t mach_result = task_get_exception_ports(
        task, g_capture_exception_mask, masks, &port_count, ports, behaviors, flavors);
    if (mach_result != KERN_SUCCESS) {
        set_capture_diagnostic("get_exception_ports_failed:kr=%d", mach_result);
        return -2;
    }

    mach_port_t exception_port = MACH_PORT_NULL;
    mach_result = mach_port_allocate(
        mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &exception_port);
    if (mach_result != KERN_SUCCESS) {
        set_capture_diagnostic("allocate_exception_port_failed:kr=%d", mach_result);
        return -2;
    }
    mach_result = mach_port_insert_right(
        mach_task_self(), exception_port, exception_port, MACH_MSG_TYPE_MAKE_SEND);
    if (mach_result != KERN_SUCCESS) {
        set_capture_diagnostic("insert_exception_right_failed:kr=%d", mach_result);
        mach_port_destroy(mach_task_self(), exception_port);
        return -2;
    }

    int result = -2;
    mach_result = task_suspend(task);
    int suspended = mach_result == KERN_SUCCESS;
    if (!suspended) {
        set_capture_diagnostic("suspend_failed:kr=%d", mach_result);
        goto cleanup;
    }
    mach_result = task_set_exception_ports(
        task, g_capture_exception_mask, exception_port, EXCEPTION_DEFAULT, THREAD_STATE_NONE);
    if (mach_result != KERN_SUCCESS) {
        set_capture_diagnostic("set_exception_port_failed:kr=%d", mach_result);
        goto cleanup;
    }
    if (configure_task_breakpoints(task, 1) != 0) {
        goto cleanup;
    }
    if (suspended) {
        task_resume(task);
        suspended = 0;
    }
    result = -1;

    fprintf(stderr, "WAITING_FOR_WECHAT_LOGIN\n");
    fflush(stderr);
    time_t deadline = time(NULL) + timeout_seconds;
    while (time(NULL) < deadline) {
        union __RequestUnion__exc_subsystem request;
        union __ReplyUnion__exc_subsystem reply;
        memset(&request, 0, sizeof(request));
        memset(&reply, 0, sizeof(reply));
        mach_msg_return_t message_result = mach_msg(
            &request.Request_exception_raise.Head,
            MACH_RCV_MSG | MACH_RCV_TIMEOUT,
            0, sizeof(request), exception_port, 1000, MACH_PORT_NULL);
        if (message_result == MACH_RCV_TIMED_OUT) {
            if (task_suspend(task) == KERN_SUCCESS) suspended = 1;
            (void)configure_task_breakpoints(task, 1);
            if (suspended) {
                task_resume(task);
                suspended = 0;
            }
            continue;
        }
        if (message_result != MACH_MSG_SUCCESS) {
            set_capture_diagnostic("receive_exception_failed:mr=%d", message_result);
            break;
        }
        if (!exc_server(&request.Request_exception_raise.Head,
                        &reply.Reply_exception_raise.Head)) {
            set_capture_diagnostic("exception_server_rejected");
            break;
        }
        message_result = mach_msg(
            &reply.Reply_exception_raise.Head, MACH_SEND_MSG,
            reply.Reply_exception_raise.Head.msgh_size, 0,
            MACH_PORT_NULL, MACH_MSG_TIMEOUT_NONE, MACH_PORT_NULL);
        if (message_result != MACH_MSG_SUCCESS) {
            set_capture_diagnostic("reply_exception_failed:mr=%d", message_result);
            break;
        }

        if (g_capture_candidate_ready) {
            memcpy(output, g_captured_passphrase, PASSPHRASE_SIZE);
            memset(g_captured_passphrase, 0, sizeof(g_captured_passphrase));
            set_capture_diagnostic("captured");
            result = 0;
            break;
        }
        if (g_capture_exception_handled) {
            usleep(10000);
            g_capture_exception_handled = 0;
            if (task_suspend(task) == KERN_SUCCESS) suspended = 1;
            if (configure_task_breakpoints(task, 1) != 0) {
                set_capture_diagnostic("rearm_hardware_breakpoint_failed");
                break;
            }
            if (suspended) {
                task_resume(task);
                suspended = 0;
            }
        }
    }

    if (result == -1 && strcmp(g_capture_diagnostic, "not_started") == 0) {
        set_capture_diagnostic("timeout:seconds=%d", timeout_seconds);
    }

cleanup:
    if (!suspended && task_suspend(task) == KERN_SUCCESS) suspended = 1;
    (void)configure_task_breakpoints(task, 0);
    restore_exception_ports(task, masks, ports, behaviors, flavors, port_count);
    if (suspended) task_resume(task);
    mach_port_destroy(mach_task_self(), exception_port);
    g_capture_task = MACH_PORT_NULL;
    return result;
}

static int attach_debugger(pid_t pid, mach_port_t *task) {
    uid_t target_uid = (uid_t)-1;
    (void)process_uid(pid, &target_uid);
    if (ptrace(PT_ATTACHEXC, pid, NULL, 0) != 0) {
        set_capture_diagnostic(
            "debug_attach_failed:pid=%d,caller_uid=%u,target_uid=%u,errno=%d",
            pid, (unsigned int)geteuid(), (unsigned int)target_uid, errno);
        return -1;
    }

    kern_return_t result = task_for_pid(mach_task_self(), pid, task);
    if (result != KERN_SUCCESS) {
        set_capture_diagnostic(
            "task_for_pid_failed:pid=%d,caller_uid=%u,target_uid=%u,kr=%d",
            pid, (unsigned int)geteuid(), (unsigned int)target_uid, result);
        (void)ptrace(PT_DETACH, pid, (caddr_t)1, 0);
        return -1;
    }
    return 0;
}

static void detach_debugger(pid_t pid, mach_port_t task) {
    int suspended = task_suspend(task) == KERN_SUCCESS;
    (void)ptrace(PT_DETACH, pid, (caddr_t)1, 0);
    if (suspended) (void)task_resume(task);
}

static void write_json_string(FILE *file, const char *value) {
    fputc('"', file);
    for (; *value; value++) {
        unsigned char character = (unsigned char)*value;
        if (character == '"' || character == '\\') {
            fputc('\\', file);
            fputc(character, file);
        } else if (character < 0x20) {
            fprintf(file, "\\u%04x", character);
        } else {
            fputc(character, file);
        }
    }
    fputc('"', file);
}

static int count_matched_databases(void) {
    int matched = 0;
    for (int index = 0; index < g_db_count; index++) {
        if (g_db_keys[index][0] != '\0') matched++;
    }
    return matched;
}

static int write_results(const char *output_path) {
    FILE *output = fopen(output_path, "w");
    if (!output) return -1;
    fprintf(output, "{\n");
    int written = 0;
    for (int db_index = 0; db_index < g_db_count; db_index++) {
        if (g_db_keys[db_index][0] == '\0') continue;
        fprintf(output, "%s  ", written ? ",\n" : "");
        write_json_string(output, g_db_paths[db_index]);
        fprintf(output, ": {\"enc_key\": \"%s\"}", g_db_keys[db_index]);
        written++;
    }
    fprintf(output, "\n}\n");
    fclose(output);
    return written;
}

static int run_capture_self_test(void) {
#if defined(__x86_64__)
    int translated = 0;
    size_t translated_size = sizeof(translated);
    if (sysctlbyname("sysctl.proc_translated", &translated, &translated_size, NULL, 0) == 0 &&
        translated == 1) {
        fprintf(stderr, "SELF_TEST_CAPTURE_SKIPPED:ROSETTA\n");
        return 0;
    }
#endif
    static const unsigned char passphrase[PASSPHRASE_SIZE] = {
        0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
        0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50,
        0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58,
        0x59, 0x5a, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36
    };
    pid_t child = fork();
    if (child < 0) return -1;
    if (child == 0) {
        struct timespec delay = {.tv_sec = 2, .tv_nsec = 0};
        while (nanosleep(&delay, &delay) != 0 && errno == EINTR) {
        }
        unsigned char derived[32];
        int result = CCKeyDerivationPBKDF(
            kCCPBKDF2, (const char *)passphrase, sizeof(passphrase),
            g_db_pages[0], 16, kCCPRFHmacAlgSHA512,
            PASSPHRASE_ROUNDS, derived, sizeof(derived));
        _exit(result == kCCSuccess ? 0 : 1);
    }

    mach_port_t task = MACH_PORT_NULL;
    if (attach_debugger(child, &task) != 0) {
        fprintf(stderr, "CAPTURE_SELF_TEST_DETAIL:attach=%s\n", g_capture_diagnostic);
        kill(child, SIGKILL);
        waitpid(child, NULL, 0);
        return -1;
    }
    unsigned char captured[PASSPHRASE_SIZE];
    int capture_result = capture_passphrase_from_task(task, 10, captured);
    detach_debugger(child, task);
    mach_port_deallocate(mach_task_self(), task);
    int child_status = 0;
    waitpid(child, &child_status, 0);
    int success = capture_result == 0 && WIFEXITED(child_status) &&
           WEXITSTATUS(child_status) == 0 &&
           memcmp(captured, passphrase, sizeof(passphrase)) == 0;
    if (!success) {
        fprintf(stderr,
                "CAPTURE_SELF_TEST_DETAIL:result=%d,child=%d,exited=%d,exit=%d,signaled=%d,signal=%d,stopped=%d,stop=%d,diagnostic=%s\n",
                capture_result, child_status, WIFEXITED(child_status),
                WIFEXITED(child_status) ? WEXITSTATUS(child_status) : -1,
                WIFSIGNALED(child_status), WIFSIGNALED(child_status) ? WTERMSIG(child_status) : -1,
                WIFSTOPPED(child_status), WIFSTOPPED(child_status) ? WSTOPSIG(child_status) : -1,
                g_capture_diagnostic);
    }
    return success ? 0 : -1;
}

static int run_derivation_self_test(void) {
    static const unsigned char passphrase[PASSPHRASE_SIZE] = {
        0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
        0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50,
        0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58,
        0x59, 0x5a, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36
    };
    unsigned char encryption_key[32];
    if (CCKeyDerivationPBKDF(
            kCCPBKDF2, (const char *)passphrase, sizeof(passphrase),
            g_db_pages[0], 16, kCCPRFHmacAlgSHA512, PASSPHRASE_ROUNDS,
            encryption_key, sizeof(encryption_key)) != kCCSuccess) {
        return -1;
    }
    char key_hex[KEY_HEX_LEN + 1];
    bytes_to_hex(encryption_key, sizeof(encryption_key), key_hex);
    unsigned char digest[CC_SHA512_DIGEST_LENGTH];
    if (calculate_page_hmac(key_hex, g_db_pages[0], digest) != 0) return -1;
    memcpy(g_db_pages[0] + SQLCIPHER_HMAC_OFFSET, digest, sizeof(digest));
    memset(g_db_keys, 0, sizeof(g_db_keys));
    return derive_keys_from_passphrase(passphrase) == 1 &&
           strcmp(g_db_keys[0], key_hex) == 0 ? 0 : -1;
}

static int run_self_test(void) {
    static const char key[] = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f";
    static const char expected_hmac[] =
        "c59b58f0b631c85658676c15a15f5d9575935c0759c0a2900000a14cfe881e0f"
        "46d453ecf18a435b39fb9e630c96ddcc961c3c0629c10968e384ab379f6a1ce1";
    for (int index = 0; index < SQLCIPHER_HMAC_OFFSET; index++) {
        g_db_pages[0][index] = (unsigned char)((index * 37 + 11) & 0xff);
    }
    bytes_to_hex(g_db_pages[0], 16, g_db_salts[0]);
    unsigned char digest[CC_SHA512_DIGEST_LENGTH];
    unsigned char expected_digest[CC_SHA512_DIGEST_LENGTH];
    if (calculate_page_hmac(key, g_db_pages[0], digest) != 0) return 1;
    if (hex_to_bytes(expected_hmac, expected_digest, sizeof(expected_digest)) != 0 ||
        memcmp(digest, expected_digest, sizeof(digest)) != 0) {
        fprintf(stderr, "SELF_TEST_FAILED:HMAC\n");
        return 1;
    }
    memcpy(g_db_pages[0] + SQLCIPHER_HMAC_OFFSET, digest, sizeof(digest));
    g_db_count = 1;

    const char *formats[] = {
        "x'000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f'",
        "x'000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f0b30557a9fc4e90e33587da2c7ec1136'",
        "x'000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1faaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa0b30557a9fc4e90e33587da2c7ec1136'"
    };
    for (size_t index = 0; index < sizeof(formats) / sizeof(formats[0]); index++) {
        memset(g_db_keys, 0, sizeof(g_db_keys));
        memset(g_seen_candidates, 0, sizeof(g_seen_candidates));
        g_seen_candidate_count = 0;
        process_memory_buffer((const unsigned char *)formats[index], strlen(formats[index]));
        if (strcmp(g_db_keys[0], key) != 0) {
            fprintf(stderr, "SELF_TEST_FAILED:%zu\n", index);
            return 1;
        }
    }
    if (run_derivation_self_test() != 0) {
        fprintf(stderr, "SELF_TEST_FAILED:DERIVATION\n");
        return 1;
    }
    if (run_capture_self_test() != 0) {
        fprintf(stderr, "SELF_TEST_FAILED:CAPTURE\n");
        return 1;
    }
    printf("SELF_TEST_OK\n");
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return run_self_test();
    if (argc == 3 && strcmp(argv[1], "--probe-task-access") == 0) {
        char *end = NULL;
        long parsed_pid = strtol(argv[2], &end, 10);
        if (end == argv[2] || *end != '\0' || parsed_pid <= 0 || parsed_pid > INT32_MAX) {
            fprintf(stderr, "INVALID_PID:%s\n", argv[2]);
            return 64;
        }
        return probe_task_access((pid_t)parsed_pid);
    }
    int capture_mode = argc >= 2 && strcmp(argv[1], "--capture-passphrase") == 0;
    if ((!capture_mode && argc != 3) || (capture_mode && argc != 4 && argc != 5)) {
        fprintf(stderr,
                "usage: %s DB_DIR OUTPUT_JSON\n"
                "       %s --capture-passphrase DB_DIR OUTPUT_JSON [TIMEOUT_SECONDS]\n",
                argv[0], argv[0]);
        return 64;
    }

    g_db_root = argv[capture_mode ? 2 : 1];
    const char *output_path = argv[capture_mode ? 3 : 2];
    int capture_timeout = DEFAULT_CAPTURE_TIMEOUT_SECONDS;
    if (capture_mode && argc == 5) {
        capture_timeout = atoi(argv[4]);
        if (capture_timeout < 5 || capture_timeout > 600) capture_timeout = DEFAULT_CAPTURE_TIMEOUT_SECONDS;
    }
    struct stat root_info;
    if (stat(g_db_root, &root_info) != 0 || !S_ISDIR(root_info.st_mode)) {
        fprintf(stderr, "DB_DIR_NOT_FOUND\n");
        return 66;
    }
    if (nftw(g_db_root, collect_database, 24, FTW_PHYS) != 0 || g_db_count == 0) {
        fprintf(stderr, "NO_ENCRYPTED_DATABASES\n");
        return 65;
    }

    pid_t pids[MAX_WECHAT_PIDS];
    int pid_count = find_wechat_pids(pids, MAX_WECHAT_PIDS);
    if (pid_count == 0) {
        fprintf(stderr, "WECHAT_NOT_RUNNING\n");
        return 69;
    }

    if (capture_mode) {
        int denied_processes = 0;
        int setup_failures = 0;
        for (int index = 0; index < pid_count; index++) {
            mach_port_t task = MACH_PORT_NULL;
            if (attach_debugger(pids[index], &task) != 0) {
                denied_processes++;
                continue;
            }
            unsigned char passphrase[PASSPHRASE_SIZE];
            int capture_result = capture_passphrase_from_task(task, capture_timeout, passphrase);
            detach_debugger(pids[index], task);
            mach_port_deallocate(mach_task_self(), task);
            if (capture_result == -2) {
                setup_failures++;
                continue;
            }
            if (capture_result != 0) continue;
            int matched = derive_keys_from_passphrase(passphrase);
            memset(passphrase, 0, sizeof(passphrase));
            if (matched == 0) {
                fprintf(stderr, "PASSPHRASE_VERIFY_FAILED:dbs=%d\n", g_db_count);
                return 2;
            }
            int written = write_results(output_path);
            if (written < 0) {
                fprintf(stderr, "OUTPUT_OPEN_FAILED\n");
                return 73;
            }
            printf("READY:%d/%d\n", written, g_db_count);
            return 0;
        }
        if (denied_processes == pid_count) {
            fprintf(stderr, "TASK_FOR_PID_DENIED:processes=%d,denied=%d,stage=%s\n",
                    pid_count, denied_processes, g_capture_diagnostic);
            return 77;
        }
        if (setup_failures > 0) {
            fprintf(stderr, "PASSPHRASE_CAPTURE_SETUP_FAILED:processes=%d,setup=%d\n",
                    pid_count, setup_failures);
            return 70;
        }
        fprintf(stderr, "PASSPHRASE_CAPTURE_TIMEOUT:seconds=%d,processes=%d\n",
                capture_timeout, pid_count);
        return 2;
    }

    int scanned_processes = 0;
    int denied_processes = 0;
    pid_t last_denied_pid = 0;
    uid_t last_denied_uid = (uid_t)-1;
    kern_return_t last_denied_result = KERN_SUCCESS;
    size_t region_count = 0;
    uint64_t byte_count = 0;
    for (int index = 0; index < pid_count && !all_databases_matched(); index++) {
        mach_port_t task = MACH_PORT_NULL;
        kern_return_t result = task_for_pid(mach_task_self(), pids[index], &task);
        if (result != KERN_SUCCESS) {
            denied_processes++;
            last_denied_pid = pids[index];
            (void)process_uid(last_denied_pid, &last_denied_uid);
            last_denied_result = result;
            continue;
        }
        scanned_processes++;
        scan_wechat_task(task, &region_count, &byte_count);
        mach_port_deallocate(mach_task_self(), task);
    }

    int matched = count_matched_databases();
    if (matched == 0) {
        if (scanned_processes == 0) {
            fprintf(stderr,
                    "TASK_FOR_PID_DENIED:processes=%d,denied=%d,pid=%d,caller_uid=%u,target_uid=%u,kr=%d\n",
                    pid_count, denied_processes, last_denied_pid,
                    (unsigned int)geteuid(), (unsigned int)last_denied_uid,
                    last_denied_result);
            return 77;
        }
        const char *error_code = g_candidate_count == 0
            ? "PASSPHRASE_REQUIRED"
            : "NO_MATCHING_KEYS";
        fprintf(stderr,
                "%s:dbs=%d,candidates=%zu,unique=%zu,processes=%d,denied=%d,regions=%zu,scanned_mb=%llu\n",
                error_code,
                g_db_count, g_candidate_count, g_unique_candidate_count,
                scanned_processes, denied_processes, region_count,
                (unsigned long long)(byte_count / (1024 * 1024)));
        return 2;
    }

    int written = write_results(output_path);
    if (written < 0) {
        fprintf(stderr, "OUTPUT_OPEN_FAILED\n");
        return 73;
    }

    printf("READY:%d/%d\n", written, g_db_count);
    return 0;
}
