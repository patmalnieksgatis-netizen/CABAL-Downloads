# Diamond v291 / current lib.so-compatible v14 source clone — dynamic offline validation

2026-11-22 | **NOT a deployable game feature**

## Exact verified input

Owner-supplied current v291 extension snapshot:
`lib.so_current_v291`, SHA256
`6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab`.

Owner-supplied v14 EventPass source bundle:
`CABAL_V282_SOURCE_v14.tar.gz`, root `source_tree/src`.
All 64 unpacked regular files have pinned manifest SHA256
`2efba153ae4d7bfcbeee2203f7b7d7a47f0a5686e31dc20dd8638ca7ac3947c2`.

The source rebuild **before adding Diamond** preserved all **144/144**
defined dynamic symbol names in the exact current v291 extension. It
had five additional exported names. This does not prove matching machine
code or state layout, but confirms v14 source is materially closer to the
currently used extension than the old archived lib.so source.

## ABI-v2 integration on an isolated SOURCE COPY only

The hash-pinned copy patcher:
`worldsvr-ingress/Apply-DiamondV14BoundClone.py` adds a
`DiamondBoundIngress::Process` call inside the v14
`ProcSystem::DoProcessDataCtx` handler for strict 18-byte
`0x09F3` candidates, **behind** passive-observe and synthetic-only
trial gates. It retains the original Gold/Platinum/EventPass and other
WorldSvr handlers unchanged. It copies the versioned verified
`diamond_merit_world_entry.cpp` and headers into the clone.

The offline v14 clone was fully linked with `-Wl,-z,defs`, the
prebuilt native rule engine and `-lodbc` into a uniquely named ELF
`libDiamondV14CompatCloneOffline.so`, SHA256:

`3a034e009076306e8be62b0af4fe5915db00dc049722f17fe4840b5e2d4a52fb`.

**Current extension export-name preservation: 144/144, missing 0**.
New candidate had 161 defined dynamic export names.

A separate synthetic x64 Linux executable used the actual
`dlopen`/`dlsym` runtime loader on that **fully linked v14 source
clone**. It dynamically located `cabal_diamond_proc_bind_shadow_clone_v2`
and `cabal_diamond_proc_test_ingress_clone_v2`. It loaded the owner's
staged 116,812-byte MeritSystem SCP, made a synthetic session/user
900001, and checked:

- Default/disabled gate: no operation
- Uninstalled host binder: no operation
- ABI v1 binder and duplicate binder: rejected
- Gold and Platinum commands: unchanged
- Untrusted user, changed first/second DWORD: rejected, no charge
- Authenticated synthetic Mastery 159 level 1: accepted
- Deliberate commit failure: rejected, with rollback
- Authenticated synthetic Mastery 159 level 2: accepted

Actual console markers:

```text
DIAMOND_LINKED_WORLDSVR_CLONE_DLOPEN=PASS
WORLD_INGRESS_V2_DYNAMIC_BIND=PASS
MALICIOUS_PACKET_NO_CHARGE=PASS
SYNTHETIC_TWO_MASTERY_LEVELS=PASS
GAME_WORLD_SESSION_OR_SQL=NOT_TESTED
```

A separate GitHub Actions run compiles the equivalent dynamic ABI-v2
test against a **synthetic shared-object shim** (since private original
source is not committed). Do not conflate that CI shim with the locally
verified owner-supplied v14 source clone.

## Important limits

The new wrapper is **not** the user's production lib.so. It was not
deployed to the VM, Docker or game client, and no real WorldSvr session
was authenticated. The current game SQL Server and actual inventory/WExp
were not modified. Neither the authentic Diamond rank-up opcode nor its
v291 S2C response semantics have been verified end to end.

In particular, the clone's original Merit dispatcher still receives a
candidate packet **after** the synthetic shadow observer; this is not
safe as a production debit path. A real Diamond implementation must
consume and reply to a fully authenticated transaction **only after**
durable game-side persistence and with confirmed client protocol.

Do not overwrite `lib.so`, use `LD_PRELOAD`, or restart WorldSvr
using this test artifact. Preserve the existing EventPass, Gold,
Platinum, Costume, dungeon and other extensions.

Reproducible private-source steps:

```sh
python3 worldsvr-ingress/Apply-DiamondV14BoundClone.py \
  --source /unpacked/CABAL_V282_SOURCE_v14/source_tree/src \
  --output /tmp/diamond_v14_clone

python3 worldsvr-ingress/Link-DiamondWorldSvrCloneLab.py \
  --clone-source /tmp/diamond_v14_clone \
  --native-lib /path/to/libDiamondNative.so \
  --merit-cpp /tmp/diamond_v14_clone/hooks/Handlers/diamond_merit_world_entry_v2.cpp \
  --baseline-current-lib /path/to/verified/lib.so_current_v291 \
  --output /tmp/diamond_v14_offline/libDiamondWorldCloneOffline.so
```
