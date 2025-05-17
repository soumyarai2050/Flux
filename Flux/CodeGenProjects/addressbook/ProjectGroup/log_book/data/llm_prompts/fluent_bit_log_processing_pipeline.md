**LLM Prompt: Fluent Bit Log Processing Pipeline (Bartering Application) - Full Context (v4.0.0)**

**Objective:** This prompt provides the complete context, final configuration, and troubleshooting history for a Fluent Bit (**v4.0.0**) log processing pipeline designed for a multi-component bartering application. Use this information as the basis for any future questions, enhancements, or troubleshooting related to this specific setup.

**1. Project Goal & Overview:**
*   Monitor log files from multiple distinct bartering application components.
*   Filter logs based on level (conditionally including DEBUG/INFO via an external script).
*   Exclude specific log patterns if needed (placeholders exist).
*   Parse logs from a specific text format into structured JSON.
*   Add component-specific metadata to records.
*   Route logs to different HTTP endpoints based on source component, log level, and message content patterns.
*   Ensure portability using environment variables for paths.
*   Send processed logs to a backend Python FastAPI application listening on specific ports/URIs.

**2. Core Technology:**
*   **Fluent Bit:** Version **4.0.0** (Installed via official `install.sh` script)
*   **Backend Receiver:** Python FastAPI application (assumed).

**3. Log Source Details:**
*   **Components Monitored:**
    *   `phone_book` (`pair_plan.log`)
    *   `street_book` (`street_book.log`)
    *   `post_book` (`post_barter.log`)
    *   `photo_book` (`plan_view.log`)
    *   `log_simulator` (writes `log_simulator_*.log` files within `street_book`'s log dir) (`log_simulator.log`)
    *   `basket_book` (`basket_book.log`)
*   **Log Format (Parsed by `custom_log_parser`):**
    ```
    YYYY-MM-DD HH:MM:SS,ms : LEVEL : [file.py : line] : Log message content
    ```
    *   `LEVEL` can be: `DEBUG`, `INFO`, `DB`, `WARNING`, `ERROR`, `CRITICAL`, `TIMING`.
*   **Parser:** `custom_log_parser` defined in `parsers.conf` handles the primary log format.

**4.1. Prerequisites / System Requirements:**
*   **Increased `inotify` Instance Limit:** Due to the architecture involving numerous Fluent Bit instances each using the `in_tail` plugin, the default kernel limit for the maximum number of `inotify` instances per user (`fs.inotify.max_user_instances`) is likely insufficient.
    *   **Requirement:** Before running the multi-process setup (e.g., 40+ instances), this limit **must** be increased.
    *   **Check Current Limit:** `sysctl fs.inotify.max_user_instances` (Default is often 128).
    *   **Recommended Value:** Increase to at least `512` or higher, depending on the total number of Fluent Bit and potentially parent application processes using file watching.
    *   **How to Apply Permanently:** Add `fs.inotify.max_user_instances = 512` (or chosen value) to `/etc/sysctl.conf` or a file in `/etc/sysctl.d/` (e.g., `/etc/sysctl.d/99-fluent-bit.conf`) and reload with `sudo sysctl -p` or reboot. Failure to do this may result in `EMFILE` ("Too many open files") errors during Fluent Bit startup.
*   **Sufficient File Descriptor Limits:** Ensure per-process (`nofile`) limits for the user running Fluent Bit are adequate. While the `EMFILE` error in this setup was traced to `inotify` instances, having a high `nofile` limit (e.g., `65536` or `1048576` via `/etc/security/limits.conf`) is good practice.
*   **Write Permissions:** The user running Fluent Bit needs write access to the `storage.path` directory (`/var/fluent-bit/state/`) for buffering and database files, and to the directory specified in `Log_File` (if configured). `sudo -E` implies root execution, which typically has permissions, but this is crucial if running as a less-privileged user.

**4.2. Execution Environment & Conditional Logic:**
*   Fluent Bit is run via a shell script (`run_fluent_bit.sh` or similar).
*   The script sets and exports two key environment variables:
    *   `FLUX_CODEGEN_BASE_DIR`: Stores the absolute base path to the project's log directories (e.g., `/home/user/.../ProjectGroup`). Used in `Path` and `Parsers_File` directives in `fluent-bit.conf`.
    *   `FILTER_LOG_LVL`: Dynamically set by the script based on a `DEBUG_MODE` shell variable.
        *   If `DEBUG_MODE=1`, `FILTER_LOG_LVL` is `^(DEBUG|INFO|DB|WARNING|ERROR|CRITICAL|TIMING)$`.
        *   If `DEBUG_MODE` is not `1`, `FILTER_LOG_LVL` is `^(DB|WARNING|ERROR|CRITICAL|TIMING)$`.
        *   This variable is used in the initial `grep` filters for most inputs to control which log levels proceed.
*   Fluent Bit is launched using `sudo -E /opt/fluent-bit/bin/fluent-bit ...` to ensure the exported environment variables are preserved and available to the `fluent-bit` process. **Note:** Permission issues preventing access to log files and the state directory (`/var/fluent-bit/state`) were resolved, allowing this method to function. (Standard security practice often involves running Fluent Bit as a dedicated, less-privileged user like `fluent` and granting specific permissions, but the current `sudo -E` approach works in this context).

**5. Final Configuration Files:**

*   **`fluent-bit.conf` (Final Version):**
    ```ini
    # ==================
    # Global Service Configuration
    # ==================
    [SERVICE]
        # Flush logs through the pipeline every 0.1 seconds for near real-time processing
        Flush        0.1
        # Run Fluent Bit as a background daemon (change to 'off' for foreground debugging)
        Daemon       off
        # Log level: error, warning, info, debug, trace
        Log_Level    info
        # Location of parsers file
        Parsers_File ${FLUX_CODEGEN_BASE_DIR}/log_book/data/parsers.conf
        # Enable built-in HTTP server for monitoring Fluent Bit itself
        HTTP_Server  On
        HTTP_Listen  0.0.0.0
        HTTP_Port    2020
        # --- Buffer Management ---
        # Use filesystem buffering to prevent data loss on crashes/restarts
        storage.path /var/fluent-bit/state/
        storage.sync normal
        storage.checksum off
        # Set memory limit for backlog buffer to 50MB
        storage.backlog.mem_limit 50M
        # Enable storage metrics (visible via HTTP_Server)
        storage.metrics on

    # ==================
    # Input #1: Pair Planegy Engine Logs
    # ==================
    [INPUT]
        Name             tail
        Alias            phone_book_logs
        Tag              pair_plan.log
        Path             ${FLUX_CODEGEN_BASE_DIR}/phone_book/log/*.log
        Path_Key         source_file
        Parser           custom_log_parser
        DB               /var/fluent-bit/state/flb_pair_plan.db
        DB.Sync          Normal
        Mem_Buf_Limit    10MB
        Refresh_Interval 2
        # Multiline support is disabled for now due to compatibility issues
        Multiline        Off
        Skip_Empty_Lines On
        Skip_Long_Lines  On
        Rotate_Wait      5
        Exit_On_Eof      false

    # ==================
    # Immediate initial Parser Filter for Pair Planegy Engine Logs
    # ==================
    [FILTER]
        Name          grep
        Match         pair_plan.log
        Regex         level ${FILTER_LOG_LVL}

    # Add any ignore regex pattern for pair_plan.log below - follow same for any input
    #[FILTER]
    #    Name          grep
    #    Match         pair_plan.log
    #    Exclude       message some_regex_pattern

    # Add component metadata to Pair Planegy logs
    [FILTER]
        Name          record_modifier
        Match         pair_plan.log
        Record        component_name phone_book
        Record        log_type bartering_engine

    # ==================
    # Input #2: Planegy Executor Logs
    # ==================
    [INPUT]
        Name             tail
        Alias            street_book_logs
        Tag              street_book.log
        Path             ${FLUX_CODEGEN_BASE_DIR}/street_book/log/street_book_*.log
        Path_Key         source_file
        Parser           custom_log_parser
        DB               /var/fluent-bit/state/flb_street_book.db
        DB.Sync          Normal
        Mem_Buf_Limit    10MB
        Refresh_Interval 2
        Multiline        Off
        Skip_Empty_Lines On
        Skip_Long_Lines  On
        Rotate_Wait      5
        Exit_On_Eof      false

    # ==================
    # Immediate initial Parser Filter for Planegy Executor Logs
    # ==================
    [FILTER]
        Name          grep
        Match         street_book.log
        Regex         level ${FILTER_LOG_LVL}

    # Add component metadata to Planegy Executor logs
    [FILTER]
        Name          record_modifier
        Match         street_book.log
        Record        component_name street_book
        Record        log_type bartering_engine

    # ==================
    # Input #3: Post Barter Engine Logs
    # ==================
    [INPUT]
        Name             tail
        Alias            post_book_logs
        Tag              post_barter.log
        Path             ${FLUX_CODEGEN_BASE_DIR}/post_book/log/*.log
        Path_Key         source_file
        Parser           custom_log_parser
        DB               /var/fluent-bit/state/flb_post_barter.db
        DB.Sync          Normal
        Mem_Buf_Limit    10MB
        Refresh_Interval 2
        Multiline        Off
        Skip_Empty_Lines On
        Skip_Long_Lines  On
        Rotate_Wait      5
        Exit_On_Eof      false

    # ==================
    # Immediate initial Parser Filter for Post Barter Engine Logs
    # ==================
    [FILTER]
        Name          grep
        Match         post_barter.log
        Regex         level ${FILTER_LOG_LVL}

    # Add component metadata to Post Barter Engine logs
    [FILTER]
        Name          record_modifier
        Match         post_barter.log
        Record        component_name post_book
        Record        log_type bartering_engine

    # ==================
    # Input #4: Planegy View Engine Logs
    # ==================
    [INPUT]
        Name             tail
        Alias            photo_book_logs
        Tag              plan_view.log
        Path             ${FLUX_CODEGEN_BASE_DIR}/photo_book/log/*.log
        Path_Key         source_file
        Parser           custom_log_parser
        DB               /var/fluent-bit/state/flb_plan_view.db
        DB.Sync          Normal
        Mem_Buf_Limit    10MB
        Refresh_Interval 2
        Multiline        Off
        Skip_Empty_Lines On
        Skip_Long_Lines  On
        Rotate_Wait      5
        Exit_On_Eof      false

    # ==================
    # Immediate initial Parser Filter for Planegy View Engine Logs
    # ==================
    [FILTER]
        Name          grep
        Match         plan_view.log
        Regex         level ${FILTER_LOG_LVL}

    # Add component metadata to Planegy View Engine logs
    [FILTER]
        Name          record_modifier
        Match         plan_view.log
        Record        component_name photo_book
        Record        log_type bartering_engine

    # ==================
    # Input #5: Log Simulator Logs
    # ==================
    [INPUT]
        Name             tail
        Alias            log_simulator_logs
        Tag              log_simulator.log
        Path             ${FLUX_CODEGEN_BASE_DIR}/street_book/log/log_simulator_*.log
        Path_Key         source_file
        Parser           custom_log_parser
        DB               /var/fluent-bit/state/flb_log_simulator.db
        DB.Sync          Normal
        Mem_Buf_Limit    10MB
        Refresh_Interval 2
        Multiline        Off
        Skip_Empty_Lines On
        Skip_Long_Lines  On
        Rotate_Wait      5
        Exit_On_Eof      false

    # ==================
    # Immediate initial Parser Filter for Log Simulator Logs
    # ==================
    [FILTER]
        Name          grep
        Match         log_simulator.log
        Regex         level ^(INFO|WARNING|ERROR|CRITICAL)$

    # Add component metadata to Log Simulator logs
    [FILTER]
        Name          record_modifier
        Match         log_simulator.log
        Record        component_name street_book_log_simulator
        Record        log_type simulation

    # ==================
    # Input #6: Basket Executor Logs
    # ==================
    [INPUT]
        Name             tail
        Alias            basket_book_logs
        Tag              basket_book.log
        Path             ${FLUX_CODEGEN_BASE_DIR}/basket_book/log/*.log
        Path_Key         source_file
        Parser           custom_log_parser
        DB               /var/fluent-bit/state/flb_basket_book.db
        DB.Sync          Normal
        Mem_Buf_Limit    10MB
        Refresh_Interval 2
        Multiline        Off
        Skip_Empty_Lines On
        Skip_Long_Lines  On
        Rotate_Wait      5
        Exit_On_Eof      false

    # ==================
    # Immediate initial Parser Filter for Basket Executor Logs
    # ==================
    [FILTER]
        Name          grep
        Match         basket_book.log
        Regex         level ${FILTER_LOG_LVL}

    # Add component metadata to Basket Executor logs
    [FILTER]
        Name          record_modifier
        Match         basket_book.log
        Record        component_name basket_book
        Record        log_type bartering_engine

    # ==================
    # Parser Filters for Pattern-Based Routing (Log Simulator)
    # ==================
    # Filter for INFO logs starting with '$$$'
    [FILTER]
        Name          grep
        Match         log_simulator.log
        Regex         level INFO
        Regex         message ^\$\$\$.*

    [FILTER]
        Name          rewrite_tag
        Match         log_simulator.log
        Rule          $message ^\$\$\$.* log_simulator.log.simulation_event false
        Emitter_Name  re_emitted_sim_events

    # Filter for WARNING, ERROR, or CRITICAL logs
    [FILTER]
        Name          grep
        Match         log_simulator.log
        Regex         level (WARNING|ERROR|CRITICAL)

    [FILTER]
        Name          rewrite_tag
        Match         log_simulator.log
        Rule          $level ^(WARNING|ERROR|CRITICAL)$ log_simulator.log.contact_alert false
        Emitter_Name  re_emitted_contact

    # ==================
    # Parser Filters for all inputs except log_simulator.log
    # ==================

    # Filter for level TIMING - use for perf benchmarking
    [FILTER]
        Name          rewrite_tag
        Match         street_book.log
        Rule          $level TIMING perf_benchmark false
        Emitter_Name  re_emitted_pref_benchmark_executor

    [FILTER]
        Name          rewrite_tag
        Match         pair_plan.log
        Rule          $level TIMING perf_benchmark false
        Emitter_Name  re_emitted_pref_benchmark_pair_plan

    [FILTER]
        Name          rewrite_tag
        Match         post_barter.log
        Rule          $level TIMING perf_benchmark false
        Emitter_Name  re_emitted_pref_benchmark_post_barter

    [FILTER]
        Name          rewrite_tag
        Match         plan_view.log
        Rule          $level TIMING perf_benchmark false
        Emitter_Name  re_emitted_pref_benchmark_plan_view

    [FILTER]
        Name          rewrite_tag
        Match         basket_book.log
        Rule          $level TIMING perf_benchmark false
        Emitter_Name  re_emitted_pref_benchmark_basket_book

    # Filter for messages starting having level DB

    [FILTER]
        Name          rewrite_tag
        Match         street_book.log
        Rule          $level DB plan_view_update false
        Emitter_Name  re_emitted_view_executor

    [FILTER]
        Name          rewrite_tag
        Match         pair_plan.log
        Rule          $level DB plan_view_update false
        Emitter_Name  re_emitted_view_pair_plan

    [FILTER]
        Name          rewrite_tag
        Match         post_barter.log
        Rule          $level DB plan_view_update false
        Emitter_Name  re_emitted_view_post_barter

    [FILTER]
        Name          rewrite_tag
        Match         plan_view.log
        Rule          $level DB plan_view_update false
        Emitter_Name  re_emitted_view_plan_view

    [FILTER]
        Name          rewrite_tag
        Match         basket_book.log
        Rule          $level DB plan_view_update false
        Emitter_Name  re_emitted_view_basket_book

    # Filter for messages with %%.*%% pattern

    [FILTER]
        Name          rewrite_tag
        Match         pair_plan.log
        Rule          $message %%.*%% symbol_side_alert false
        Emitter_Name  re_emitted_symbol_side_pair_plan

    [FILTER]
        Name          rewrite_tag
        Match         post_barter.log
        Rule          $message %%.*%% symbol_side_alert false
        Emitter_Name  re_emitted_symbol_side_post_barter

    [FILTER]
        Name          rewrite_tag
        Match         plan_view.log
        Rule          $message %%.*%% symbol_side_alert false
        Emitter_Name  re_emitted_symbol_side_plan_view

    [FILTER]
        Name          rewrite_tag
        Match         basket_book.log
        Rule          $message %%.*%% symbol_side_alert false
        Emitter_Name  re_emitted_symbol_side_basket_book

    # ==================
    # Output Configuration for Log Simulator Logs
    # ==================
    # Output for INFO logs with '$$$' pattern
    [OUTPUT]
        Name             http
        Alias            simulator_events_output
        Match            log_simulator.log.simulation_event
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_simulate_log
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on
        net.keepalive_idle_timeout 30

    # Output for WARNING/ERROR/CRITICAL logs (contact alerts)
    [OUTPUT]
        Name             http
        Alias            contact_alerts_output
        Match            log_simulator.log.contact_alert
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_contact_alerts
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # ==================
    # Output Configuration for Other Inputs
    # ==================
    # Output for level DB
    [OUTPUT]
        Name             http
        Alias            plan_view_updates_output
        Match            plan_view_update
        Host             127.0.0.1
        Port             8070
        URI              /photo_book/query-handle_plan_view_updates
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # Output for all street_book logs that haven't been rewritten
    [OUTPUT]
        Name             http
        Alias            street_book_alerts_output
        Match            street_book.log
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_plan_alerts_with_plan_id
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # Output for messages with %%.*%% pattern (excluding street_book)
    [OUTPUT]
        Name             http
        Alias            symbol_side_alerts_output
        Match            symbol_side_alert
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_plan_alerts_with_symbol_side
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # Output for perf benchmark
    [OUTPUT]
        Name             http
        Alias            perf_benchmark_output
        Match            perf_benchmark
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_perf_benchmark
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # Default output for remaining pair_plan.log
    [OUTPUT]
        Name             http
        Alias            default_pair_plan_alerts_output
        Match            pair_plan.log
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_contact_alerts
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # Default output for remaining post_barter.log
    [OUTPUT]
        Name             http
        Alias            default_post_barter_alerts_output
        Match            post_barter.log
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_contact_alerts
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # Default output for remaining plan_view.log
    [OUTPUT]
        Name             http
        Alias            default_plan_view_alerts_output
        Match            plan_view.log
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_contact_alerts
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # Default output for remaining basket_book.log
    [OUTPUT]
        Name             http
        Alias            default_basket_book_alerts_output
        Match            basket_book.log
        Host             127.0.0.1
        Port             8030
        URI              /log_book/query-handle_contact_alerts
        Format           json
        Json_Date_Format iso8601
        Json_Date_Key    timestamp
        allow_duplicated_headers false
        Retry_Limit      5
        tls              Off
        tls.verify       Off
        Workers          4
        net.keepalive    on

    # Metrics and Monitoring Output
    [OUTPUT]
        Name  prometheus_exporter
        Match *
        Host  0.0.0.0
        Port  2021
    ```

*   **`parsers.conf` (Final Version):**
    ```ini
    # ==================
    # Parser Configuration
    # ==================

    # ==================
    # Custom Log Parser (DEBUG|INFO|DB|WARNING|ERROR|CRITICAL|TIMING)
    # ==================
    [PARSER]
        # Parser name (referenced in the INPUT section)
        Name        custom_log_parser
        # Type of format (regex, json, logfmt, etc.)
        Format      regex
        # Regular expression pattern to parse custom log format
        # Captures: time, level, file, line, and message
        Regex       ^(?<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) : (?<level>DEBUG|INFO|DB|WARNING|ERROR|CRITICAL|TIMING) : \[(?<file>[^\s:]+) : (?<line>\d+)\] : (?<message>.*)$
        # Field that contains the timestamp
        Time_Key    time
        # Time format (strftime-compatible)
        # %L is milliseconds
        Time_Format %Y-%m-%d %H:%M:%S,%L
        # Data types for specific fields
        Types       line:integer

    # ==================
    # Multiline Parser Configuration
    # ==================
    # This is preserved but not currently used as multiline is disabled
    [PARSER]
        Name        multiline_parser
        Format      regex
        Regex       ^(?<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})
        Time_Key    time
        Time_Format %Y-%m-%d %H:%M:%S,%L

    # ==================
    # JSON Parser
    # ==================
    [PARSER]
        Name        json_parser
        Format      json
        Time_Key    timestamp
        Time_Format %Y-%m-%d %H:%M:%S,%L
    ```

**6. Backend Receiver Summary:**
*   Logs are sent via HTTP POST to endpoints on `127.0.0.1`.
*   Two ports are used: `8030` and `8070`.
*   The backend application (e.g., Python FastAPI) must listen on both ports and handle the specified URIs.
*   Fluent Bit sends logs batched as a **JSON array** of record objects: `[ {record1}, {record2}, ... ]`.
*   The `nest` filter is **not** used; the backend should **not** expect a `{"payload": ...}` wrapper around each record.

**7. Key Troubleshooting Decisions & History:**
*   Resolved initial **duplicate input paths** by using distinct file patterns (`street_book_*.log` vs. `log_simulator_*.log`).
*   Corrected initial `grep` filters to operate on the **parsed `level` field** instead of the raw `log` field, understanding filter execution chore relative to the parser.
*   Solved **environment variable expansion** issues by using `sudo -E` to preserve the environment when running Fluent Bit.
*   Diagnosed **HTTP 422 errors** from the backend; determined Fluent Bit sends a JSON array by default, and the backend needed adjustment (or Fluent Bit needed the `nest` filter, which was ultimately removed).
*   Corrected **URI mismatches** between Fluent Bit outputs and backend endpoint definitions.
*   Refined **`rewrite_tag` logic** using separate filters per input tag for clarity and robustness, especially for `DB` and `TIMING` levels.
*   Implemented **conditional log level filtering** (`FILTER_LOG_LVL`) via environment variables set by an external script.
*   Uninstalled previous Fluent Bit version and **reinstalled v4.0.0** using the official install script.
*   Resolved **permission issues** allowing Fluent Bit (when run via `sudo -E`) to access logs and the state directory.
*   **Resolved `EMFILE` ("Too many open files") errors and associated defunct Fluent Bit processes** that occurred when running many (e.g., 40) Fluent Bit instances concurrently via Python `subprocess`.
    *   **Initial checks confirmed** that per-process file descriptor limits (`ulimit -n`) were high (`1048576`) and correctly inherited by child processes, and the system-wide limit (`fs.file-max`) was effectively unlimited.
    *   **Root Cause Identified:** The errors stemmed from exceeding the kernel's per-user limit for **`inotify` instances** (`fs.inotify.max_user_instances`), which often defaults to a low value like `128`. Each Fluent Bit process using the `in_tail` input plugin creates at least one `inotify` instance to monitor log files efficiently. The cumulative demand from 40 Fluent Bit processes (plus potentially the 40 parent Python processes if they also use file watching) surpassed this limit, causing startup failures manifesting as `EMFILE`.
    *   **Solution Implemented:** The `fs.inotify.max_user_instances` limit was increased (e.g., to `512`) using `sudo sysctl -w fs.inotify.max_user_instances=512`.
    *   **Permanence:** The change was made permanent by adding `fs.inotify.max_user_instances = 512` (or the chosen value) to `/etc/sysctl.conf` or a file within `/etc/sysctl.d/` and reloading with `sudo sysctl -p` or rebooting.
    *   **Why Needed & Barter-offs:** This increase is necessary to accommodate the architectural choice of running numerous independent Fluent Bit processes, each requiring its own `inotify` resources.
        *   **Pro:** Allows the multi-process architecture to function correctly without hitting this specific kernel limit.
        *   **Con:** Each `inotify` instance consumes a small amount of non-swappable kernel memory. Increasing the limit allows more kernel memory to be potentially allocated for this purpose. However, increasing from 128 to 512 for ~80 required instances is generally a minor resource consideration on modern systems and justifiable for the application's needs.

**8. Final Routing Logic Summary:**
*   **Initial Filtering:** Logs from most components are first filtered by level based on `${FILTER_LOG_LVL}`. `log_simulator` keeps `INFO|WARN|ERR|CRIT`.
*   **Exclusions:** Placeholders exist immediately after initial level filtering to add `grep`/`Exclude` rules if needed.
*   **Log Simulator Routing:**
    *   `INFO` level + message starts `$$$` -> Tag `log_simulator.log.simulation_event` -> Port 8030 `/log_book/query-handle_simulate_log`
    *   `WARN|ERR|CRIT` levels -> Tag `log_simulator.log.contact_alert` -> Port 8030 `/log_book/query-handle_contact_alerts`
*   **Performance Benchmarking Routing:**
    *   `TIMING` level from *any* monitored component -> Tag `perf_benchmark` -> Port 8030 `/log_book/query-handle_perf_benchmark`
*   **Planegy View Update Routing:**
    *   `DB` level from `pair_plan`, `street_book`, `post_barter`, `plan_view`, `basket_book` -> Tag `plan_view_update` -> Port 8070 `/photo_book/query-handle_plan_view_updates`
*   **Symbol/Side Alert Routing:**
    *   Message contains `%%...%%` from `pair_plan`, `post_barter`, `plan_view`, `basket_book` (**Note:** Does **not** currently match `street_book`) -> Tag `symbol_side_alert` -> Port 8030 `/log_book/query-handle_plan_alerts_with_symbol_side`
*   **Planegy Executor Specific Routing:**
    *   Any log remaining with tag `street_book.log` (including `WARN|ERR|CRIT` and potentially messages with `%%...%%` if not matched above) -> Port 8030 `/log_book/query-handle_plan_alerts_with_plan_id`
*   **Default Routing:**
    *   Any log remaining with original tags `pair_plan.log`, `post_barter.log`, `plan_view.log`, or `basket_book.log` -> Port 8030 `/log_book/query-handle_contact_alerts`

**9. Future Considerations:**
*   The commented-out `Exclude` filter blocks provide a designated place to add pattern-based log line exclusions per input source if required. Simply uncomment and add `Exclude message <your_regex>` lines as needed within the relevant filter block. Remember one `Exclude` rule per block for OR logic.
*   Confirm if `street_book` logs with `%%...%%` should be routed to the `symbol_side_alert` endpoint or remain routed to the `street_book_alerts_output`. If they should go to `symbol_side_alert`, add the appropriate `rewrite_tag` filter.