# CABAL Diamond — durable native transaction proof (2026-11-22)

## Concrete deliverable

A native C++17 **disk-backed SQLite test host** has been compiled and executed against the exact private, staged 116,812-byte `MeritSystem.scp` and the previously built `libDiamondNative.so` with the authenticated `cabal_diamond_world_execute` C ABI.

The complete tested source is **also permanently committed** at [`diamond_sqlite_testhost.cpp`](./diamond_sqlite_testhost.cpp); a synthetic full-catalog emitter is committed at [`test_emit_synthetic_scp.cpp`](./test_emit_synthetic_scp.cpp). Linux CI rebuilds the host from these exact files, links `libDiamondNative.so` and real SQLite, and verifies disk persistence/rollback/concurrent replay **using synthetic config**: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/45003138779 (PASS). The Linux binary, source, `.so`, user's private staged SCP, synthetic-user SQLite DB, manifest, and usage notes are also in the conversation artifact **`CABAL_Diamond_Durable_TestHost_20261122.zip`**, SHA256 `319ce5c9db54337f5503d6416d4e9addc3567d9f0517789a3ad179ba475a7389`. The **private SCP is not committed to public GitHub**.

### Exact actual execution

```text
DIAMOND_SQLITE_DURABLE_BRIDGE=PASS
RESTART_PERSISTENCE=PASS
ROLLBACK=PASS
CONCURRENT_REPLAY=PASS
REAL_SCP_MASTERIES=316;DATA_STORE=ISOLATED_SQLITE_TEST_ONLY
PRODUCTION_SQL_SERVER_OR_WORLDSVR=NO
PERSISTED_ACCOUNT [(900001, badge=2, wexp=10000, tickets=20, mastery_points=90, revision=13)]
PERSISTED_MASTERY [(900001, mastery_id=159, level=2)]
```

- Test account UserNum 900001 is **synthetic** and exists ONLY in the generated SQLite test DB. No CABAL player record was accessed.
- Initial state: synthetic Platinum grade 1, WExp 40,000, item-count 120, mastery points 100, revision 10.
- Tested rank up using real staged grade-2 requirements: -30,000 WExp, -100 item tickets, revision 11.
- Tested rank-up replay rejection, injected DB commit failure/rollback with persisted state unchanged, Mastery ID 159 level-1 purchase, and **4 concurrent same-revision level-2 purchases with only 1 durable commit**.
- The actual staged SCP makes Mastery 159 cost 5 points at **both** level 1 and level 2, yielding remaining mastery points 90 and final revision 13.
- SQLite `BEGIN IMMEDIATE`, user+revision compare-and-swap and one transaction for *synthetic account* resources/masteries produced the durable result. The test was reopened with independent sqlite3 inspection.

### Verified prior legacy WorldSvrRealm extension source

Recovered actual user-provided `CABAL_EXTRA_SOURCE.tar.gz` (10,715,254 bytes) and inspected `root/projects/WorldSvr/Proc/Proc.cpp`, `Proc/Proc.h`, `PacketManager/Protodefs.h`, `PacketManager/C2SPackets.h`. This archived **extension**, NOT the current proprietary v291 WorldSvr, exposes:

- `Proc::Init()` registers `OnProcessCustomPackets` for `MAINCMD_VALUE_EX::CSC_CUSTOM_PACKET` (=421 in its own historical enum).
- `Proc::OnProcessCustomPackets` reads `C2S_HEADER_EX.extCmd` and executes `m_procedures[extCmd]` callbacks via `REGISTER.../RegisterProcedure`.
- `PROCESSDATACONTEXT` carries `pUserCtx`, `cpPacket`, `iLen`; other historical extension code accesses `USERCONTEXT`, `USERDATACONTEXT`, `bIsActvteLink` and `GetUserNum()`.
- **Do not silently reuse** the example's numerical main command 421 or its user-context/layout/absolute function pointers: its compatibility with the running v291 WorldSvr, actual Diamond Merit opcode or packet structure has **not** been verified. The source's callback return handling also deserves independent inspection before any implementation because `P_OK=0` but the dispatcher tests `if (!callback(...))`.
- There is no Diamond, Platinum, or Merit C2S handler in this extension code. Therefore it does **not** close the missing packet binding.

## Next *actual game* gate

To make this playable, we need the verified **current** WorldSvr Merit opcode registration and native authenticated session context, plus inventory and WExp storage and MSSQL transaction ABI, not another generic .enc/client hex collector. No active WorldSvr, Docker, `Server01`, original MeritSystem.scp, or Gold/Platinum player data was touched.

**Do not install this SQLite/GLIBC_2.38 test binary into the game container.** This test proves durable transaction logic with real rules, not real client->WorldSvr->SQL game integration.

## CI details

GitHub Actions run `45003138779` compiled all native tests and this disk-backed host; final job **success**. Log confirms `DIAMOND_SQLITE_DURABLE_BRIDGE=PASS`, `RESTART_PERSISTENCE=PASS`, `ROLLBACK=PASS`, `CONCURRENT_REPLAY=PASS`. CI runs the synthetic configuration; private staged SCP was tested **locally** with the same binary code only, not uploaded to GitHub.
