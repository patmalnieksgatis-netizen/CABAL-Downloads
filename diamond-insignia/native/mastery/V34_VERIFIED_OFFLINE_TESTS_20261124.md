# V34 verified offline test results
Date: 2026-11-24
Source commit: 40986855572feca28f91e6ef62657bf2af8bf6f9

Four fetched source files were reproduced in an isolated temporary directory and their git blob SHA-1 values checked against GitHub before compilation:

- native/diamond_rules.hpp: 1ae5fb3a9304120a28d9af7ece5150fb66908ab4
- native/mastery/DiamondMasteryTransaction.hpp: 55802ceca7aba156b16c644a0af41a7bf85d8168
- worldsvr-ingress/test_mastery_rules_v32.cpp: 75f466319aec5abeb1b2260df4a98c1f76ca51c5
- worldsvr-ingress/test_mastery_transaction_v33.cpp: 0b81764434275c2036ef759162890a316c497281

Compiler: g++ (Debian 14.2.0-19) 14.2.0.
Flags: -std=c++17 -Wall -Wextra -Werror -O2.
Both binaries compiled and executed with exit status zero:
```
DIAMOND_V32_RULES=PASS
DIAMOND_MASTERY_TRANSACTION_FIXTURE=PASS
```

These are actual isolated tests with synthetic state, not live acceptance tests. GitHub Actions results were not available via the queried status endpoints.

Remaining functional integration blockers: a supported, authorized server extension interface and verified owner/session lifecycle; verified native Diamond data formats and mastery catalog semantics; an actual storage implementation with independent synchronization and recovery proof; client compatibility and end-to-end game verification. The fixture storage is not a production backend. Do not count the passing tests as proof of any of these prerequisites. V29 last reported forwarding-only; no game VM, SQL, client, or core library changes were performed in this test run.
