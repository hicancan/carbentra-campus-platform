/* Host-only integration fixture. Link the actual Switch decoder and core, with
 * cJSON from its approved source; no networking, GPIO or physical execution. */
#include <string.h>
#include "command_json.h"

int main(int argc, char **argv) {
    switch_command_t command;
    if (argc != 2) return 2;
    return command_json_decode(argv[1], strlen(argv[1]), &command) ? 0 : 1;
}
